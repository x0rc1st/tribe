"""TRIBE v2 model wrapper — loads model, accepts content, returns vertex activations."""

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class BrainPredictor:
    """Wraps TribeModel for inference."""

    def __init__(self, model_repo: str, cache_dir: str, device: str = "auto"):
        self.model_repo = model_repo
        self.cache_dir = cache_dir
        self.device = device
        self.model = None

    def load(self):
        """Load TRIBE v2 model from HuggingFace."""
        from tribev2 import TribeModel

        logger.info("Loading TRIBE v2 from %s ...", self.model_repo)
        self.model = TribeModel.from_pretrained(
            self.model_repo,
            cache_folder=self.cache_dir,
            device=self.device,
        )
        logger.info("TRIBE v2 loaded successfully.")

    def predict_text(self, text: str) -> tuple[np.ndarray, list]:
        """Predict brain activations from text content.

        Returns:
            preds: (n_timesteps, 20484) cortical vertex activations
            segments: aligned segment metadata
        """
        assert self.model is not None, "Model not loaded. Call load() first."

        # Write text to temp file (TRIBE v2 expects a file path)
        tmp_path = Path(self.cache_dir) / "tmp_input.txt"
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(text, encoding="utf-8")

        try:
            df = self.model.get_events_dataframe(text_path=str(tmp_path))
            preds, segments = self.model.predict(events=df, verbose=True)
            logger.info("Prediction shape: %s", preds.shape)
            return preds, segments
        finally:
            tmp_path.unlink(missing_ok=True)

    def predict_video(self, video_path: str) -> tuple[np.ndarray, list]:
        """Predict brain activations from video file.

        Returns:
            preds: (n_timesteps, 20484) cortical vertex activations
            segments: aligned segment metadata
        """
        assert self.model is not None, "Model not loaded. Call load() first."

        df = self.model.get_events_dataframe(video_path=video_path)
        preds, segments = self.model.predict(events=df, verbose=True)
        logger.info("Prediction shape: %s", preds.shape)
        return preds, segments

    def predict_audio(self, audio_path: str) -> tuple[np.ndarray, list]:
        """Predict brain activations from audio file.

        Returns:
            preds: (n_timesteps, 20484) cortical vertex activations
            segments: aligned segment metadata
        """
        assert self.model is not None, "Model not loaded. Call load() first."

        df = self.model.get_events_dataframe(audio_path=audio_path)
        preds, segments = self.model.predict(events=df, verbose=True)
        logger.info("Prediction shape: %s", preds.shape)
        return preds, segments
