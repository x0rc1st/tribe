"""Skill Mastery & ORI API routes.

POST /api/v1/mastery/{operator_id}/completions  — record a completion
GET  /api/v1/mastery/{operator_id}/skills       — skill mastery overview
GET  /api/v1/mastery/{operator_id}/ori           — ORI composite score
GET  /api/v1/mastery/{operator_id}/completions   — completion history
DELETE /api/v1/mastery/{operator_id}             — clear operator data
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mastery", tags=["mastery"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RecordCompletionRequest(BaseModel):
    course_id: str = Field(..., description="Unique course/module identifier")
    completion_type: str = Field(
        ...,
        description="Brain-derived type: 'procedural', 'analytical', or 'operational'",
    )
    skill_tags: list[str] = Field(
        ..., description="Skill IDs this completion contributes to",
    )
    group_z_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Cognitive group z-scores from prediction (optional, for audit)",
    )


class RecordCertificationRequest(BaseModel):
    cert_id: str
    skill_tags: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_store(request: Request):
    store = getattr(request.app.state, "mastery_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Mastery store not initialized")
    return store


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/{operator_id}/completions")
async def record_completion(operator_id: str, body: RecordCompletionRequest, request: Request):
    """Record a course completion for an operator.

    The completion_type should come from the /api/v1/predict response's
    completion_type field (brain-derived classification).
    """
    store = _get_store(request)

    if body.completion_type not in ("procedural", "analytical", "operational"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid completion_type '{body.completion_type}'. "
                   f"Must be 'procedural', 'analytical', or 'operational'.",
        )

    gz = {int(k): v for k, v in body.group_z_scores.items()} if body.group_z_scores else {}

    result = store.record_completion(
        operator_id=operator_id,
        course_id=body.course_id,
        completion_type=body.completion_type,
        skill_tags=body.skill_tags,
        group_z_scores=gz,
    )
    return result


@router.post("/{operator_id}/certifications")
async def record_certification(operator_id: str, body: RecordCertificationRequest, request: Request):
    """Record a certification for an operator."""
    store = _get_store(request)
    return store.record_certification(
        operator_id=operator_id,
        cert_id=body.cert_id,
        skill_tags=body.skill_tags,
    )


@router.get("/{operator_id}/skills")
async def get_skills(operator_id: str, request: Request):
    """Return skill mastery state for all skills."""
    store = _get_store(request)
    return store.get_skills(operator_id)


@router.get("/{operator_id}/ori")
async def get_ori(operator_id: str, request: Request, role_id: str | None = None):
    """Compute ORI score for an operator."""
    store = _get_store(request)
    return store.get_ori(operator_id, role_id=role_id)


@router.get("/{operator_id}/completions")
async def get_completions(operator_id: str, request: Request):
    """Return completion history for an operator."""
    store = _get_store(request)
    return store.get_completions(operator_id)


@router.delete("/{operator_id}")
async def delete_operator(operator_id: str, request: Request):
    """Delete all mastery data for an operator."""
    store = _get_store(request)
    deleted = store.delete_operator(operator_id)
    return {"operator_id": operator_id, "deleted_records": deleted}
