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


class CompletionTopGroup(BaseModel):
    id: int
    name: str
    z_score: float


class CompletionBreakdownEntry(BaseModel):
    """Classification result for a specific top_n setting."""
    type: str
    top_n: int
    rule: str
    triggered_group_ids: list[int]
    top_groups: list[CompletionTopGroup]


class CompositionVector(BaseModel):
    """Continuous (conceptual, procedural, operational) values that sum to 1.0."""
    conceptual: float
    procedural: float
    operational: float


class CompositionTopGroup(BaseModel):
    id: int
    name: str
    z_score: float
    engagement_pct: float = 0.0


class CompletionCompositionResponse(BaseModel):
    """Per-text composition vector + bucket contributions in the same shape that
    `/api/v1/classify` returns and that ORI uses to accumulate mastery."""
    raw_intensities: CompositionVector
    composition: CompositionVector
    thresholds: dict[str, int]
    bucket_contributions: CompositionVector
    total_points: float
    tau: float
    top_groups: list[CompositionTopGroup]


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
    completion_type: str = Field(
        default="conceptual",
        description=(
            "Brain-derived completion type for Algorithm v3.2: "
            "'conceptual' (building mental models — fronto-parietal dominant), "
            "'procedural' (building motor skills — G2 sensorimotor dominant), or "
            "'operational' (performing under pressure — G9 threat + cognitive co-activation)"
        ),
    )
    completion_breakdown: dict[str, CompletionBreakdownEntry] | None = Field(
        default=None,
        description=(
            "Classification computed at multiple top-N settings (keys '3', '4', '5'). "
            "Each entry exposes the decision rule and the top groups inspected so the "
            "UI can justify the result and let the user explore N=4 and N=5."
        ),
    )
    completion_composition: CompletionCompositionResponse | None = Field(
        default=None,
        description=(
            "Continuous conceptual / procedural / operational scores for this text — "
            "the same composition vector and bucket contributions that "
            "/api/v1/classify returns and that ORI uses to accumulate mastery."
        ),
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
