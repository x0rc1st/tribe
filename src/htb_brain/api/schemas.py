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
    engagement_pct: float = 0.0
    brain_area: str
    neuroscience: str
    offensive: str
    defensive: str
    operator_frame: str
    region_scores: dict[str, float]


class SubcorticalRegionResponse(BaseModel):
    """One subcortical structure in the prediction response."""
    name: str
    z_score: float
    group_ids: list[int]
    engaged: bool = False


# ---------------------------------------------------------------------------
# Operator Readiness
# ---------------------------------------------------------------------------

class DimensionResponse(BaseModel):
    """One operator readiness dimension in the prediction response."""
    key: str
    name: str
    strength: float
    srk_mode: str
    details: dict


class OperatorDimensionsResponse(BaseModel):
    """All 6 operator readiness dimensions for a prediction."""
    procedural_automaticity: DimensionResponse
    threat_detection: DimensionResponse
    situational_awareness: DimensionResponse
    strategic_decision: DimensionResponse
    analytical_synthesis: DimensionResponse
    stress_resilience: DimensionResponse


class PredictResponse(BaseModel):
    """Full response from the /api/v1/predict endpoint."""
    vertex_activations: list[float] = Field(
        ...,
        description="Activation values normalised to 0-1. First 20484 are cortical (fsaverage5), remaining are subcortical mesh vertices (if subcortical model is loaded).",
    )
    group_scores: list[GroupScoreResponse] = Field(
        ...,
        description="Capability-group scores sorted by rank (includes subcortical contributions)",
    )
    narrative_summary: str = Field(
        ...,
        description="Markdown narrative summarising brain engagement",
    )
    engaged_regions: list[str] = Field(
        ...,
        description="Destrieux region names above the engagement threshold",
    )
    subcortical_regions: list[SubcorticalRegionResponse] = Field(
        default_factory=list,
        description="Subcortical structure activations (empty if subcortical model not loaded)",
    )
    n_cortical_vertices: int = Field(
        default=20484,
        description="Number of cortical vertices in vertex_activations",
    )
    n_subcortical_vertices: int = Field(
        default=0,
        description="Number of subcortical mesh vertices appended after cortical",
    )
    operator_readiness: OperatorDimensionsResponse | None = Field(
        default=None,
        description="6-dimension operator readiness profile derived from brain engagement",
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    model_loaded: bool
    gpu_name: str
    gpu_memory: str
    atlas_loaded: bool
    subcortical_loaded: bool = False
