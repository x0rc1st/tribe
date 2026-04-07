"""Subcortical model wrapper — loads fine-tuned subcortical checkpoint, returns voxel activations."""

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class SubcorticalPredictor:
    """Loads a fine-tuned subcortical TRIBE v2 model and runs inference.

    This is the subcortical counterpart of BrainPredictor. It loads a
    checkpoint trained with MaskProjector(mask="subcortical") and outputs
    per-voxel subcortical activations instead of cortical vertices.

    The model architecture is identical to the cortical model — only the
    final prediction head dimension differs (N_subcortical instead of 20484).
    """

    def __init__(self, checkpoint_dir: str, cache_dir: str, device: str = "auto"):
        self.checkpoint_dir = checkpoint_dir
        self.cache_dir = cache_dir
        self.device = device
        self.model = None
        self._raw_model = None
        self.n_outputs = 0

    def load(self):
        """Load the fine-tuned subcortical model from checkpoint.

        Loads the checkpoint directly (bypassing TribeExperiment validation)
        and averages multi-subject weights into a single prediction head.
        """
        import gc
        import torch
        import yaml

        ckpt_dir = Path(self.checkpoint_dir)

        ckpt_name = "best.ckpt"
        if not (ckpt_dir / ckpt_name).exists():
            ckpt_name = "last.ckpt"
        if not (ckpt_dir / ckpt_name).exists():
            raise FileNotFoundError(
                f"No checkpoint found in {ckpt_dir}. "
                f"Expected best.ckpt or last.ckpt"
            )

        logger.info("Loading subcortical model from %s ...", ckpt_dir)

        # Load config and checkpoint directly (bypasses study validation)
        config_path = ckpt_dir / "config.yaml"
        with open(config_path) as f:
            cfg = yaml.load(f, Loader=yaml.UnsafeLoader)

        ckpt = torch.load(
            ckpt_dir / ckpt_name, map_location="cpu", weights_only=True, mmap=True
        )
        build_args = ckpt["model_build_args"]
        state_dict = {
            k.removeprefix("model."): v for k, v in ckpt["state_dict"].items()
        }
        self.n_outputs = build_args["n_outputs"]
        del ckpt
        gc.collect()

        # Average subject weights if multi-subject checkpoint
        if "predictor.weights" in state_dict:
            w = state_dict["predictor.weights"]
            if w.shape[0] > 1:
                state_dict["predictor.weights"] = w.mean(dim=0, keepdim=True)
                logger.info("Averaged %d subject weights -> 1", w.shape[0])
        if "predictor.bias" in state_dict:
            b = state_dict["predictor.bias"]
            if b.shape[0] > 1:
                state_dict["predictor.bias"] = b.mean(dim=0, keepdim=True)

        # Build model from checkpoint config
        from tribev2.model import FmriEncoder
        brain_cfg = cfg["brain_model_config"]
        brain_cfg["subject_layers"] = brain_cfg.get("subject_layers", {})
        brain_cfg["subject_layers"]["average_subjects"] = True
        brain_cfg["subject_layers"]["n_subjects"] = 0
        model_config = FmriEncoder(**{k: v for k, v in brain_cfg.items() if k != "name"})
        model = model_config.build(**build_args)
        model.load_state_dict(state_dict, strict=True, assign=True)
        del state_dict
        gc.collect()

        device = "cuda" if torch.cuda.is_available() else "cpu" if self.device == "auto" else self.device
        model.to(device)
        model.eval()
        self._raw_model = model

        logger.info(
            "Subcortical model loaded: %d output voxels, device=%s",
            self.n_outputs, device,
        )

    def predict_text(self, text: str) -> tuple[np.ndarray, list]:
        """Predict subcortical activations from text.

        Uses the cortical TribeModel for event processing, then runs
        the subcortical model on the same features.
        """
        assert self._raw_model is not None, "Model not loaded. Call load() first."

        from tribev2 import TribeModel
        import torch
        from einops import rearrange
        from tqdm import tqdm

        cortical = TribeModel.from_pretrained(
            "facebook/tribev2", cache_folder=self.cache_dir, device=self.device
        )

        tmp_path = Path(self.cache_dir) / "tmp_subcort_input.txt"
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(text, encoding="utf-8")

        try:
            df = cortical.get_events_dataframe(text_path=str(tmp_path))
            loader = cortical.data.get_loaders(events=df, split_to_build="all")["all"]

            preds, all_segments = [], []
            with torch.inference_mode():
                for batch in tqdm(loader, desc="Subcortical"):
                    batch = batch.to(next(self._raw_model.parameters()).device)
                    batch_segments = []
                    for segment in batch.segments:
                        for t in np.arange(0, segment.duration - 1e-2, cortical.data.TR):
                            batch_segments.append(segment.copy(offset=t, duration=cortical.data.TR))

                    keep = np.array([len(s.ns_events) > 0 for s in batch_segments])
                    batch_segments = [s for i, s in enumerate(batch_segments) if keep[i]]

                    y_pred = self._raw_model(batch).detach().cpu().numpy()
                    y_pred = rearrange(y_pred, "b d t -> (b t) d")[keep]
                    preds.append(y_pred)
                    all_segments.extend(batch_segments)

            preds = np.concatenate(preds)
            logger.info("Subcortical prediction shape: %s", preds.shape)
            return preds, all_segments
        finally:
            tmp_path.unlink(missing_ok=True)

    def predict_video(self, video_path: str) -> tuple[np.ndarray, list]:
        """Predict subcortical activations from video file."""
        assert self._raw_model is not None, "Model not loaded. Call load() first."

        from tribev2 import TribeModel
        import torch
        from einops import rearrange
        from tqdm import tqdm

        cortical = TribeModel.from_pretrained(
            "facebook/tribev2", cache_folder=self.cache_dir, device=self.device
        )
        df = cortical.get_events_dataframe(video_path=video_path)
        loader = cortical.data.get_loaders(events=df, split_to_build="all")["all"]

        preds, all_segments = [], []
        with torch.inference_mode():
            for batch in tqdm(loader, desc="Subcortical video"):
                batch = batch.to(next(self._raw_model.parameters()).device)
                batch_segments = []
                for segment in batch.segments:
                    for t in np.arange(0, segment.duration - 1e-2, cortical.data.TR):
                        batch_segments.append(segment.copy(offset=t, duration=cortical.data.TR))

                keep = np.array([len(s.ns_events) > 0 for s in batch_segments])
                batch_segments = [s for i, s in enumerate(batch_segments) if keep[i]]

                y_pred = self._raw_model(batch).detach().cpu().numpy()
                y_pred = rearrange(y_pred, "b d t -> (b t) d")[keep]
                preds.append(y_pred)
                all_segments.extend(batch_segments)

        preds = np.concatenate(preds)
        logger.info("Subcortical prediction shape: %s", preds.shape)
        return preds, all_segments

    def predict_audio(self, audio_path: str) -> tuple[np.ndarray, list]:
        """Predict subcortical activations from audio file."""
        assert self._raw_model is not None, "Model not loaded. Call load() first."

        from tribev2 import TribeModel
        import torch
        from einops import rearrange
        from tqdm import tqdm

        cortical = TribeModel.from_pretrained(
            "facebook/tribev2", cache_folder=self.cache_dir, device=self.device
        )
        df = cortical.get_events_dataframe(audio_path=audio_path)
        loader = cortical.data.get_loaders(events=df, split_to_build="all")["all"]

        preds, all_segments = [], []
        with torch.inference_mode():
            for batch in tqdm(loader, desc="Subcortical audio"):
                batch = batch.to(next(self._raw_model.parameters()).device)
                batch_segments = []
                for segment in batch.segments:
                    for t in np.arange(0, segment.duration - 1e-2, cortical.data.TR):
                        batch_segments.append(segment.copy(offset=t, duration=cortical.data.TR))

                keep = np.array([len(s.ns_events) > 0 for s in batch_segments])
                batch_segments = [s for i, s in enumerate(batch_segments) if keep[i]]

                y_pred = self._raw_model(batch).detach().cpu().numpy()
                y_pred = rearrange(y_pred, "b d t -> (b t) d")[keep]
                preds.append(y_pred)
                all_segments.extend(batch_segments)

        preds = np.concatenate(preds)
        logger.info("Subcortical prediction shape: %s", preds.shape)
        return preds, all_segments
