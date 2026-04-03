"""POST /api/v1/aggregate — cross-unit aggregation (stub)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/v1", tags=["aggregate"])


@router.post(
    "/aggregate",
    summary="Aggregate predictions across multiple learning units (stub)",
    status_code=501,
)
async def aggregate():
    """Placeholder for cross-unit aggregation.

    Accepts a list of per-unit prediction results and returns a combined
    engagement profile.  Not yet implemented.
    """
    return JSONResponse(
        status_code=501,
        content={
            "detail": "Cross-unit aggregation is not yet implemented. "
                      "Use /api/v1/predict for single-unit predictions."
        },
    )
