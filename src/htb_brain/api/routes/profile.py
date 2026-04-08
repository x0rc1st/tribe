"""Operator Readiness Profile API routes.

Phase 2: POST /api/v1/profile/{operator_id}/modules — record module scores
         GET  /api/v1/profile/{operator_id}         — return readiness profile

Phase 3: GET  /api/v1/profile/{operator_id}/gaps    — dependency-aware gap analysis
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from htb_brain.core.operator_readiness import (
    detect_dimensions,
    detect_gaps,
    extract_readiness_inputs,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/profile", tags=["operator-readiness"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RecordModuleRequest(BaseModel):
    """Record a module's brain engagement data for an operator."""
    module_id: str = Field(..., description="Unique module identifier")
    module_name: str = Field(default="", description="Human-readable module name")
    group_scores: list[dict] = Field(
        ...,
        description="GroupScoreResponse list from /api/v1/predict (needs 'id' and 'z_score')",
    )
    subcortical_regions: list[dict] = Field(
        default_factory=list,
        description="SubcorticalRegionResponse list from /api/v1/predict",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_store(request: Request):
    """Get the ProfileStore from app state."""
    store = getattr(request.app.state, "profile_store", None)
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="Profile store not initialized",
        )
    return store


# ---------------------------------------------------------------------------
# Phase 2: Profile accumulation
# ---------------------------------------------------------------------------

@router.post("/{operator_id}/modules")
async def record_module(operator_id: str, body: RecordModuleRequest, request: Request):
    """Record a module's dimension scores for an operator.

    Takes the group_scores and subcortical_regions from a /api/v1/predict
    response and computes + stores the 6 readiness dimensions.
    """
    store = _get_store(request)

    # Convert predict response format to detect_dimensions input
    gs_dict, sc_dict = extract_readiness_inputs(
        body.group_scores, body.subcortical_regions,
    )

    # Compute dimensions
    dimensions = detect_dimensions(gs_dict, sc_dict)

    # Store
    result = store.record_module(
        operator_id=operator_id,
        module_id=body.module_id,
        module_name=body.module_name,
        group_scores=gs_dict,
        subcortical_scores=sc_dict,
        dimensions=dimensions,
    )

    return result


@router.get("/{operator_id}")
async def get_profile(operator_id: str, request: Request):
    """Return the accumulated readiness profile for an operator."""
    store = _get_store(request)
    profile = store.get_profile(operator_id)

    if profile["total_modules"] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No modules recorded for operator '{operator_id}'",
        )

    return profile


# ---------------------------------------------------------------------------
# Phase 3: Gap detection & recommendations
# ---------------------------------------------------------------------------

@router.get("/{operator_id}/gaps")
async def get_gaps(operator_id: str, request: Request):
    """Dependency-aware gap analysis with SRK error risk.

    Returns gaps sorted by actionability (unblocked first) and severity.
    Respects DEPENDENCY_ORDER: won't recommend stress resilience training
    if procedural automaticity is still a gap.
    """
    store = _get_store(request)
    profile = store.get_profile(operator_id)

    if profile["total_modules"] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No modules recorded for operator '{operator_id}'",
        )

    rdns = {
        dim_key: dim_data["readiness"]
        for dim_key, dim_data in profile["dimensions"].items()
    }

    gaps = detect_gaps(rdns)

    return {
        "operator_id": operator_id,
        "total_modules": profile["total_modules"],
        "dimension_readiness": rdns,
        "gaps": gaps,
        "all_clear": len(gaps) == 0,
    }


@router.delete("/{operator_id}")
async def delete_profile(operator_id: str, request: Request):
    """Delete all records for an operator."""
    store = _get_store(request)
    deleted = store.delete_operator(operator_id)
    return {"operator_id": operator_id, "deleted_modules": deleted}
