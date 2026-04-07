#!/usr/bin/env python3
"""
Fine-tune TRIBE v2 pretrained backbone for subcortical predictions.

The released facebook/tribev2 checkpoint only predicts cortical surface
activations (20,484 fsaverage5 vertices). This script reuses the trained
multimodal transformer backbone and attaches a fresh prediction head
targeting subcortical voxels (Harvard-Oxford atlas in MNI space).

Architecture overview:
    [text/audio/video] -> projectors -> 8-layer transformer -> low_rank_head
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        These layers are loaded from the pretrained cortical checkpoint.

    -> SubjectLayers(2048, N_subcortical)
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
       This prediction head is randomly initialized and trained.

Requirements:
    - tribev2 with training + plotting extras:
        pip install -e "/path/to/tribev2[training,plotting]"
    - At least one fMRI dataset with volumetric (MNI) bold data:
        Algonauts2025Bold, Wen2017, Lahner2024Bold, or Lebel2023Bold
    - GPU with >= 24 GB VRAM (A100/H100/RTX 4090+)

Environment variables:
    DATAPATH   — root directory containing the fMRI study datasets
    SAVEPATH   — directory for output checkpoints and logs
    HF_TOKEN   — HuggingFace token (for downloading the pretrained model)

Usage:
    # Set paths
    export DATAPATH=/workspace/data
    export SAVEPATH=/workspace/tribe/subcortical_training
    export HF_TOKEN=hf_...

    # Train head only (fastest, recommended first)
    python scripts/train_subcortical.py --freeze-backbone

    # Full fine-tune (backbone lr=1e-5, head lr=1e-4)
    python scripts/train_subcortical.py

    # Train on a single dataset
    python scripts/train_subcortical.py --studies Algonauts2025Bold --freeze-backbone

    # Use mini config (smaller feature extractors, faster iteration)
    python scripts/train_subcortical.py --mini --freeze-backbone

    # Resume from a previous subcortical checkpoint
    python scripts/train_subcortical.py --resume /path/to/last.ckpt
"""

import argparse
import copy
import gc
import logging
import os
import sys
from pathlib import Path

import numpy as np
import torch

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s %(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("train_subcortical")


# ---------------------------------------------------------------------------
# Subcortical mask (matches tribev2.plotting.subcortical.get_subcortical_mask)
# ---------------------------------------------------------------------------

def get_subcortical_mask():
    """Return the Harvard-Oxford subcortical binary mask.

    This replicates the logic from tribev2/plotting/subcortical.py so that
    the voxel order in our predictions matches the MaskProjector used during
    training.
    """
    from nilearn import datasets
    import nibabel as nib

    atlas = datasets.fetch_atlas_harvard_oxford("sub-maxprob-thr50-2mm")
    excluded = ["Cortex", "White", "Stem", "Background"]
    excluded_indices = [
        i for i, label in enumerate(atlas.labels)
        if any(exc.lower() in label.lower() for exc in excluded)
    ]
    mask_data = atlas.maps.get_fdata().copy()
    mask_data[np.isin(mask_data, excluded_indices)] = 0
    mask = nib.Nifti1Image(mask_data, atlas.maps.affine, atlas.maps.header)
    return mask


def count_subcortical_voxels():
    """Count how many voxels the subcortical mask contains."""
    mask = get_subcortical_mask()
    n = int((mask.get_fdata() > 0).sum())
    logger.info("Subcortical mask: %d non-zero voxels", n)
    return n


# ---------------------------------------------------------------------------
# Config builder
# ---------------------------------------------------------------------------

def build_subcortical_config(args):
    """Build a TribeExperiment config dict for subcortical training."""
    # Import here so the top-level script can show --help without tribev2
    from tribev2.grids.defaults import default_config
    from tribev2.grids.configs import mini_config
    from exca import ConfDict

    base = mini_config if args.mini else default_config
    config = ConfDict(copy.deepcopy(dict(base)))

    # --- Paths ---
    datadir = os.environ.get("DATAPATH", "/workspace/data")
    savedir = os.environ.get("SAVEPATH", "/workspace/tribe/subcortical_training")
    cachedir = os.path.join(savedir, "cache")
    resultsdir = os.path.join(savedir, "results")

    for d in [cachedir, resultsdir]:
        Path(d).mkdir(parents=True, exist_ok=True)

    config["infra.folder"] = resultsdir
    config["infra.cluster"] = None  # local training (no SLURM)
    config["data.study.path"] = datadir

    # --- Replace cortical SurfaceProjector with subcortical MaskProjector ---
    config["data.neuro"] = {
        "name": "FmriExtractor",
        "allow_missing": True,
        "offset": 5,
        "frequency": 1,
        "projection": {
            "name": "MaskProjector",
            "mask": "subcortical",
        },
        "fwhm": 6.0,
        "=replace=": True,
    }
    # Update neuro infra for local
    config["data.neuro.infra"] = {
        "folder": cachedir,
        "mode": "cached",
        "max_jobs": 1,
    }

    # --- Studies ---
    if args.studies:
        config["data.study.names"] = (
            args.studies if len(args.studies) > 1 else args.studies[0]
        )
    # else: keep default (all 4 studies)

    # --- Feature extractor caching (local, no SLURM) ---
    for feat in ["text_feature", "audio_feature", "video_feature", "image_feature"]:
        config[f"data.{feat}.infra.folder"] = cachedir
        config[f"data.{feat}.infra.cluster"] = None
        config[f"data.{feat}.infra.mode"] = "cached"

    # --- Training hyperparameters ---
    config["n_epochs"] = args.epochs
    config["data.batch_size"] = args.batch_size
    config["data.num_workers"] = args.num_workers
    config["patience"] = args.patience
    config["enable_progress_bar"] = True
    config["seed"] = 42

    # --- Disable wandb unless explicitly requested ---
    if not args.wandb:
        config["wandb_config"] = None

    # --- Do NOT load a checkpoint through TribeExperiment ---
    config["load_checkpoint"] = False
    config["checkpoint_path"] = None

    # --- Subject handling ---
    config["average_subjects"] = args.average_subjects

    # --- Hardware ---
    config["infra.gpus_per_node"] = 1
    config["infra.cpus_per_task"] = args.num_workers or 8

    # Remove SLURM-specific keys
    for key in ["infra.slurm_partition", "infra.slurm_constraint", "infra.workdir"]:
        config.pop(key, None)

    # Remove study infra_timelines (use local)
    config["data.study.infra_timelines"] = {
        "folder": cachedir,
        "max_jobs": 1,
    }

    return config


# ---------------------------------------------------------------------------
# Backbone weight injection
# ---------------------------------------------------------------------------

def download_cortical_checkpoint(cache_dir: str) -> Path:
    """Download the pretrained cortical checkpoint from HuggingFace."""
    from huggingface_hub import hf_hub_download

    logger.info("Downloading pretrained cortical checkpoint from facebook/tribev2...")
    ckpt_path = hf_hub_download("facebook/tribev2", "best.ckpt", cache_dir=cache_dir)
    logger.info("Downloaded to: %s", ckpt_path)
    return Path(ckpt_path)


def inject_backbone_weights(pl_module, cortical_ckpt_path: Path):
    """Load backbone weights from a cortical checkpoint into the subcortical model.

    Loads everything EXCEPT the prediction head (SubjectLayers), which has
    a different output dimension for subcortical targets.
    """
    logger.info("Loading cortical checkpoint: %s", cortical_ckpt_path)
    ckpt = torch.load(
        cortical_ckpt_path, map_location="cpu", weights_only=True, mmap=True
    )
    cortical_state = ckpt["state_dict"]
    del ckpt
    gc.collect()

    # Filter out prediction head keys (shape mismatch: 20484 vs N_subcortical)
    backbone_state = {
        k: v for k, v in cortical_state.items()
        if "predictor" not in k
    }
    del cortical_state
    gc.collect()

    # Count what we're loading
    model_keys = set(pl_module.state_dict().keys())
    loading_keys = set(backbone_state.keys())
    matched = model_keys & loading_keys
    skipped_model = model_keys - loading_keys
    skipped_ckpt = loading_keys - model_keys

    logger.info(
        "Backbone injection: %d matched, %d skipped (model-only), %d skipped (ckpt-only)",
        len(matched), len(skipped_model), len(skipped_ckpt),
    )

    # Verify shapes match for all keys we're loading
    model_state = pl_module.state_dict()
    for key in matched:
        if model_state[key].shape != backbone_state[key].shape:
            logger.warning(
                "Shape mismatch for %s: model=%s, ckpt=%s — skipping",
                key, model_state[key].shape, backbone_state[key].shape,
            )
            del backbone_state[key]

    pl_module.load_state_dict(backbone_state, strict=False)
    logger.info("Backbone weights loaded successfully.")

    # Log which components are pretrained vs random
    predictor_params = sum(
        p.numel() for n, p in pl_module.named_parameters() if "predictor" in n
    )
    total_params = sum(p.numel() for p in pl_module.parameters())
    logger.info(
        "Parameters: %d total, %d predictor (%.1f%% random init)",
        total_params, predictor_params, 100 * predictor_params / max(total_params, 1),
    )


def freeze_backbone_params(pl_module):
    """Freeze all parameters except the prediction head."""
    frozen = 0
    trainable = 0
    for name, param in pl_module.named_parameters():
        if "predictor" in name:
            param.requires_grad = True
            trainable += param.numel()
        else:
            param.requires_grad = False
            frozen += param.numel()
    logger.info(
        "Froze backbone: %d params frozen, %d trainable (predictor only)", frozen, trainable
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune TRIBE v2 for subcortical brain predictions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--freeze-backbone", action="store_true",
        help="Freeze the pretrained backbone, train only the prediction head (faster)",
    )
    parser.add_argument(
        "--studies", nargs="+",
        choices=["Algonauts2025Bold", "Wen2017", "Lahner2024Bold", "Lebel2023Bold"],
        help="Which fMRI dataset(s) to train on (default: all 4)",
    )
    parser.add_argument(
        "--mini", action="store_true",
        help="Use smaller feature extractors (Qwen3-0.6B, vjepa2-vitl) for faster iteration",
    )
    parser.add_argument(
        "--epochs", type=int, default=15,
        help="Number of training epochs (default: 15)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=8,
        help="Batch size (default: 8)",
    )
    parser.add_argument(
        "--num-workers", type=int, default=8,
        help="DataLoader workers (default: 8)",
    )
    parser.add_argument(
        "--patience", type=int, default=5,
        help="Early stopping patience (default: 5, set 0 to disable)",
    )
    parser.add_argument(
        "--resume", type=str, default=None,
        help="Resume from a subcortical checkpoint (skips backbone injection)",
    )
    parser.add_argument(
        "--skip-pretrained", action="store_true",
        help="Train from scratch (no pretrained backbone)",
    )
    parser.add_argument(
        "--average-subjects", action="store_true",
        help="Average across subjects (single shared prediction head)",
    )
    parser.add_argument(
        "--wandb", action="store_true",
        help="Enable Weights & Biases logging",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Quick sanity check (1 batch, no real training)",
    )
    args = parser.parse_args()

    if args.patience == 0:
        args.patience = None

    # --- Validate environment ---
    datapath = os.environ.get("DATAPATH")
    savepath = os.environ.get("SAVEPATH", "/workspace/tribe/subcortical_training")

    if not datapath:
        logger.error(
            "DATAPATH not set. Point it to the directory containing fMRI datasets.\n"
            "  export DATAPATH=/workspace/data\n"
            "Each dataset should be a subdirectory (e.g., DATAPATH/download/...).\n"
            "See tribev2/studies/ for dataset structure requirements."
        )
        sys.exit(1)

    if not Path(datapath).is_dir():
        logger.error("DATAPATH=%s does not exist", datapath)
        sys.exit(1)

    Path(savepath).mkdir(parents=True, exist_ok=True)

    # --- Count subcortical voxels (validates nilearn + atlas availability) ---
    n_voxels = count_subcortical_voxels()
    logger.info("Will train model with %d subcortical output voxels", n_voxels)

    # --- Build config ---
    config = build_subcortical_config(args)

    if args.dry_run:
        config["fast_dev_run"] = True
        config["n_epochs"] = 1

    # --- Create experiment ---
    import lightning.pytorch as pl
    from tribev2.main import TribeExperiment

    xp = TribeExperiment(**config)
    xp.setup_run()

    pl.seed_everything(xp.seed, workers=True)

    # --- Build data loaders ---
    logger.info("Building data loaders (this extracts features — may take a while)...")
    loaders = xp.data.get_loaders()

    if "train" not in loaders:
        logger.error(
            "No training data found. Check that DATAPATH contains the expected "
            "dataset structure and that the study name is correct."
        )
        sys.exit(1)

    train_loader = loaders["train"]
    val_loader = loaders.get("val", train_loader)

    # --- Build model + trainer ---
    logger.info("Building model and trainer...")
    xp._setup_trainer(train_loader)

    # Log the actual output dimension (determined from data)
    model = xp._model.model
    logger.info(
        "Model built: n_outputs=%d, feature_dims=%s",
        model.n_outputs, model.feature_dims,
    )

    # --- Inject pretrained backbone ---
    if args.resume:
        resume_path = Path(args.resume)
        if not resume_path.exists():
            logger.error("Resume checkpoint not found: %s", resume_path)
            sys.exit(1)
        logger.info("Resuming from: %s (skipping backbone injection)", resume_path)
        ckpt = torch.load(resume_path, map_location="cpu", weights_only=True)
        xp._model.load_state_dict(ckpt["state_dict"], strict=True)
        del ckpt
        gc.collect()
    elif not args.skip_pretrained:
        cache_dir = os.path.join(savepath, "hf_cache")
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        cortical_ckpt = download_cortical_checkpoint(cache_dir)
        inject_backbone_weights(xp._model, cortical_ckpt)
    else:
        logger.info("Training from scratch (no pretrained backbone)")

    # --- Optionally freeze backbone ---
    if args.freeze_backbone:
        freeze_backbone_params(xp._model)

    # --- Train ---
    logger.info("Starting training...")
    xp.fit(train_loader, val_loader)

    # --- Evaluate ---
    logger.info("Evaluating on validation set...")
    xp.test(val_loader)

    # --- Save inference-ready checkpoint info ---
    results_dir = Path(config["infra.folder"])
    best_ckpt = results_dir / "best.ckpt"
    last_ckpt = results_dir / "last.ckpt"

    if best_ckpt.exists():
        logger.info("Best checkpoint: %s", best_ckpt)
    elif last_ckpt.exists():
        logger.info("Last checkpoint: %s", last_ckpt)
    else:
        logger.warning("No checkpoint found — training may have been too short.")

    logger.info(
        "Training complete. To use this model for inference:\n"
        "  from htb_brain.core.subcortical_predictor import SubcorticalPredictor\n"
        "  pred = SubcorticalPredictor('%s', cache_dir='./cache')\n"
        "  pred.load()\n"
        "  result = pred.predict_text('your text here')",
        results_dir,
    )


if __name__ == "__main__":
    main()
