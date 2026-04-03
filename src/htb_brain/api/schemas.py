"""Pydantic request/response schemas for the HTB Brain API."""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class PredictTextRequest(BaseModel):
    """JSON body for the /api/v1/predict endpoint."""
    text: str = Field(..., description="Text content to predict brain engagement for")
    content_type: str = Field(
        default="text module",
        description="Label for the kind of content (e.g. 'text module', 'lab recording')",
    )


# ---------------------------------------------------------------------------
# Response sub-models
# ---------------------------------------------------------------------------

class GroupScoreResponse(BaseModel):
    """One capability-group score in the prediction response."""
    id: int
    name: str
    score: float
    z_score: float
    rank: int
    brain_area: str
    neuroscience: str
    offensive: str
    defensive: str
    operator_frame: str
    region_scores: dict[str, float]


class PredictResponse(BaseModel):
    """Full response from the /api/v1/predict endpoint."""
    vertex_activations: list[float] = Field(
        ...,
        description="20484 activation values normalised to 0-1 for the fsaverage5 surface",
    )
    group_scores: list[GroupScoreResponse] = Field(
        ...,
        description="Capability-group scores sorted by rank",
    )
    narrative_summary: str = Field(
        ...,
        description="Markdown narrative summarising brain engagement",
    )
    engaged_regions: list[str] = Field(
        ...,
        description="Destrieux region names above the engagement threshold",
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    model_loaded: bool
    gpu_name: str
    gpu_memory: str
    atlas_loaded: bool
