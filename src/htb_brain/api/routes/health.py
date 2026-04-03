"""GET /health — service health check."""

import logging

from fastapi import APIRouter, Request

from htb_brain.api.schemas import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Service health check")
async def health(request: Request):
    """Return model/atlas status and GPU information."""

    # Model loaded?
    predictor = getattr(request.app.state, "predictor", None)
    model_loaded = predictor is not None and predictor.model is not None

    # Atlas loaded?
    atlas = getattr(request.app.state, "atlas", None)
    atlas_loaded = atlas is not None and atlas._loaded

    # GPU info
    gpu_name = "N/A"
    gpu_memory = "N/A"
    try:
        import torch

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            mem = torch.cuda.get_device_properties(0).total_mem
            gpu_memory = f"{mem / (1024 ** 3):.1f} GB"
    except Exception:
        logger.debug("Could not query GPU info", exc_info=True)

    return HealthResponse(
        model_loaded=model_loaded,
        gpu_name=gpu_name,
        gpu_memory=gpu_memory,
        atlas_loaded=atlas_loaded,
    )
