"""POST /api/v1/aggregate — combine multiple prediction results."""

import logging

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from htb_brain.api.dependencies import get_atlas, get_translator
from htb_brain.core.atlas import BrainAtlas
from htb_brain.core.translator import Translator
from htb_brain.api.routes.predict import _get_vertex_groups

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["aggregate"])


class AggregateRequest(BaseModel):
    predictions: list[dict]
    labels: list[str] = []


@router.post("/aggregate")
async def aggregate(
    body: AggregateRequest,
    atlas: BrainAtlas = Depends(get_atlas),
    translator: Translator = Depends(get_translator),
):
    """Combine multiple predictions into an aggregated view with comparison."""
    if len(body.predictions) < 2:
        raise HTTPException(422, "Need at least 2 predictions to aggregate")

    try:
        n = len(body.predictions)
        labels = body.labels if len(body.labels) == n else [f"Input {i+1}" for i in range(n)]

        # Stack vertex activations
        all_verts = []
        for p in body.predictions:
            verts = p.get("vertex_activations", [])
            if len(verts) != 20484:
                raise HTTPException(422, f"Expected 20484 activations, got {len(verts)}")
            all_verts.append(verts)

        cumulative = np.mean(np.array(all_verts, dtype=np.float32), axis=0)

        # Per-prediction group scores
        per_pred = []
        for p in body.predictions:
            per_pred.append({g["name"]: g["score"] for g in p.get("group_scores", [])})

        # Cumulative + variance
        all_names = sorted(set().union(*(pg.keys() for pg in per_pred)))
        comparison = []
        for name in all_names:
            vals = [pg.get(name, 0.0) for pg in per_pred]
            comparison.append({
                "name": name,
                "cumulative_score": round(float(np.mean(vals)), 3),
                "variance": round(float(np.var(vals)), 4),
                "per_input": {labels[i]: round(vals[i], 3) for i in range(n)},
            })

        comparison.sort(key=lambda x: x["cumulative_score"], reverse=True)
        differential = sorted(comparison, key=lambda x: x["variance"], reverse=True)

        return {
            "vertex_activations": cumulative.tolist(),
            "vertex_groups": _get_vertex_groups(atlas, translator),
            "comparison": comparison,
            "most_differential": [{"name": d["name"], "variance": d["variance"]} for d in differential[:5]],
            "labels": labels,
            "n_inputs": n,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Aggregation failed")
        raise HTTPException(500, str(e))
