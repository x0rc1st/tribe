"""GET /api/v1/classify/{entity_id} — brain-derived completion type for an entity.

Returns deterministic mock group z-scores and the resulting completion type
for any entity UUID. Uses a seeded RNG so the same entity_id always produces
the same classification.

Also supports POST for batch classification of multiple entities.
"""

import hashlib
import logging
import random

from fastapi import APIRouter
from pydantic import BaseModel, Field

from htb_brain.core.completion_classifier import (
    COGNITIVE_GROUPS,
    TOP_N,
    classify_completion,
    completion_points,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["classify"])

GROUP_NAMES = {
    1: "Strategic Thinking & Decision-Making",
    2: "Procedural Fluency & Muscle Memory",
    3: "Technical Comprehension & Language",
    4: "Visual Processing & Pattern Detection",
    5: "Situational Awareness & Focus",
    6: "Motivation & Adaptive Drive",
    7: "Memory Encoding & Knowledge Retention",
    8: "Knowledge Synthesis & Transfer",
    9: "Threat Awareness & Emotional Encoding",
    10: "Deep Internalization & Reflection",
}


def _mock_z_scores(entity_id: str) -> dict[int, float]:
    """Generate deterministic mock z-scores from an entity UUID.

    Uses SHA-256 of the entity_id as a seed so the same ID always
    produces the same scores.  The distribution is shaped to produce
    a realistic mix of procedural / analytical / operational outcomes.
    """
    digest = hashlib.sha256(entity_id.encode()).hexdigest()
    seed = int(digest[:16], 16)
    rng = random.Random(seed)

    scores: dict[int, float] = {}
    for gid in range(1, 11):
        # Base z-score: normal-ish distribution centered at 0, sd ~0.8
        z = rng.gauss(0.0, 0.8)
        scores[gid] = round(z, 4)

    # Give one or two groups a realistic boost so top-3 patterns emerge
    boost_count = rng.choice([1, 2, 2, 3])
    boost_groups = rng.sample(range(1, 11), boost_count)
    for gid in boost_groups:
        scores[gid] += rng.uniform(0.8, 1.8)
        scores[gid] = round(scores[gid], 4)

    return scores


def _build_response(entity_id: str) -> dict:
    """Build a full classification response for one entity."""
    group_z_scores = _mock_z_scores(entity_id)
    completion_type = classify_completion(group_z_scores)
    points = completion_points(completion_type)

    # Build ranked group list
    ranked = sorted(group_z_scores.items(), key=lambda x: x[1], reverse=True)
    top_ids = {gid for gid, _ in ranked[:TOP_N]}

    groups = []
    for rank, (gid, z) in enumerate(ranked, 1):
        marker = None
        if gid in top_ids:
            if gid == 2:
                marker = "PROCEDURAL"
            elif gid in COGNITIVE_GROUPS:
                marker = "ANALYTICAL"
            if gid == 9:
                marker = "OPERATIONAL"
        groups.append({
            "rank": rank,
            "group_id": gid,
            "name": GROUP_NAMES[gid],
            "z_score": round(z, 4),
            "in_top_3": gid in top_ids,
            "marker": marker,
        })

    return {
        "entity_id": entity_id,
        "completion_type": completion_type,
        "points": points,
        "group_z_scores": {str(k): v for k, v in group_z_scores.items()},
        "groups_ranked": groups,
    }


# ---------------------------------------------------------------------------
# GET — single entity
# ---------------------------------------------------------------------------

@router.get("/classify/{entity_id}")
async def classify_entity(entity_id: str):
    """Return brain-derived completion type for an entity.

    Produces deterministic mock z-scores seeded by the entity_id,
    then classifies using the top-3 brain region logic.

    The same entity_id always returns the same result.
    """
    return _build_response(entity_id)


# ---------------------------------------------------------------------------
# POST — batch classification
# ---------------------------------------------------------------------------

class BatchClassifyRequest(BaseModel):
    entity_ids: list[str] = Field(..., description="List of entity UUIDs to classify")


@router.post("/classify")
async def classify_batch(body: BatchClassifyRequest):
    """Classify multiple entities in one request.

    Returns a list of classification results, one per entity_id.
    """
    results = [_build_response(eid) for eid in body.entity_ids]

    # Summary counts
    counts = {"procedural": 0, "analytical": 0, "operational": 0}
    for r in results:
        counts[r["completion_type"]] += 1

    return {
        "total": len(results),
        "distribution": counts,
        "results": results,
    }
