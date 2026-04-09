"""POST /api/v1/predict — async job-based prediction pipeline."""

import asyncio
import hashlib
import logging
import threading
import time
import uuid
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request

from htb_brain.api.dependencies import (
    get_predictor, get_atlas, get_translator,
    get_subcortical_predictor, get_subcortical_atlas, get_subcortical_aggregator,
)
from htb_brain.api.schemas import PredictResponse, GroupScoreResponse
from htb_brain.core.aggregator import Aggregator
from htb_brain.core.atlas import BrainAtlas
from htb_brain.core.predictor import BrainPredictor
from htb_brain.core.translator import Translator
from htb_brain.core.completion_classifier import classify_completion
from htb_brain.core.operator_readiness import detect_dimensions, extract_readiness_inputs
from htb_brain.visualization.summary import generate_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["predict"])

# ── Job store (in-memory) ────────────────────────────────────────────────

_jobs: dict[str, dict[str, Any]] = {}
_result_cache: dict[str, dict] = {}  # text_hash -> result dict


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode()).hexdigest()[:16]


# ── Subcortical helpers ──────────────────────────────────────────────────

def _run_subcortical(text: str, sc_predictor, sc_atlas, sc_aggregator, mesh_meta_path: str | None, cortical_model=None):
    """Run subcortical prediction and return enrichment data.

    Returns dict with subcortical_vertex_activations, subcortical_regions,
    subcortical_group_contributions, or None if subcortical is not available.
    """
    if sc_predictor is None:
        return None

    try:
        sc_preds, _ = sc_predictor.predict_text(text, cortical_model=cortical_model)
        sc_result = sc_aggregator.process_prediction(sc_preds)

        # Map voxel activations to mesh vertices (for 3D rendering)
        mesh_vertex_acts = None
        if mesh_meta_path:
            from htb_brain.visualization.subcortical_mesh_export import map_voxel_activations_to_mesh
            mean_act = np.mean(sc_preds, axis=0).astype(np.float32)
            # Normalize 0-1
            vmin, vmax = mean_act.min(), mean_act.max()
            if vmax - vmin > 0:
                mean_act = (mean_act - vmin) / (vmax - vmin)
            else:
                mean_act = np.zeros_like(mean_act)
            mesh_vertex_acts = map_voxel_activations_to_mesh(mean_act, mesh_meta_path)

        return {
            "regions": sc_result["regions"],
            "region_zscores": sc_result["region_zscores"],
            "engaged_regions": sc_result["engaged_regions"],
            "group_scores": sc_result["group_scores"],
            "mesh_vertex_activations": mesh_vertex_acts,
        }
    except Exception:
        logger.exception("Subcortical prediction failed — returning cortical-only result")
        return None


# Per-group evidence weights (lazy-loaded from subcortical_cognitive_map.json)
_evidence_weights: dict[int, float] | None = None


def _get_evidence_weights() -> dict[int, float]:
    """Load per-group evidence weights from the subcortical cognitive map."""
    global _evidence_weights
    if _evidence_weights is None:
        import json
        from pathlib import Path
        map_path = Path(__file__).resolve().parent.parent.parent / "data" / "subcortical_cognitive_map.json"
        with open(map_path) as f:
            data = json.load(f)
        _evidence_weights = {g["id"]: g.get("evidence_weight", 0.0) for g in data["groups"]}
        logger.info("Loaded subcortical evidence weights: %s", _evidence_weights)
    return _evidence_weights


import copy

# Neuroscience-based beta weights for equal-quality subcortical model.
# These reflect the actual cortical/subcortical contribution per cognitive
# function based on published neuroscience (see design doc).
NEUROSCIENCE_BETAS: dict[int, float] = {
    1: 0.40,   # G1 Strategic: caudate drives reward-based learning loops
    2: 0.70,   # G2 Procedural: automaticity LIVES in putamen/pallidum
    3: 0.15,   # G3 Language: overwhelmingly cortical, thalamus relays
    # G4: no subcortical mapping
    5: 0.25,   # G5 SA: thalamic reticular nucleus gates attention
    6: 0.60,   # G6 Motivation: accumbens IS the reward engine
    7: 0.75,   # G7 Memory: hippocampus IS memory encoding (patient H.M.)
    # G8: no subcortical mapping
    9: 0.65,   # G9 Threat: amygdala IS threat detection (LeDoux's low road)
    # G10: no subcortical mapping
}


def _blend_groups(cortical_groups: list, subcortical_group_scores: dict, betas: dict[int, float]) -> list:
    """Blend subcortical into cortical using given beta weights. Returns a new list."""
    groups = copy.deepcopy(cortical_groups)
    for gs in groups:
        gid = gs["id"]
        if gid not in subcortical_group_scores or gid not in betas:
            continue
        sc_contrib = subcortical_group_scores[gid]
        beta = betas[gid]
        if beta > 0:
            gs["score"] = gs["score"] * (1 - beta) + sc_contrib * beta
            gs["z_score"] = gs["score"]

    # Re-rank
    groups.sort(key=lambda x: x["score"], reverse=True)
    max_z = max(gs["score"] for gs in groups) if groups else 1.0
    max_z = max(max_z, 0.01)
    for i, gs in enumerate(groups):
        gs["rank"] = i + 1
        gs["engagement_pct"] = round(max(0.0, gs["score"] / max_z) * 100, 1)

    return groups


def _merge_group_scores(cortical_groups: list, subcortical_group_scores: dict | None) -> list:
    """Blend subcortical group contributions into cortical group scores.

    Uses per-group evidence weights (from cognitive map) scaled by the global
    reliability discount (from config). Groups without subcortical mapping
    are unaffected.
    """
    if not subcortical_group_scores:
        return cortical_groups

    from htb_brain.config import settings
    evidence_weights = _get_evidence_weights()
    reliability = settings.subcortical_reliability
    betas = {gid: ew * reliability for gid, ew in evidence_weights.items()}

    return _blend_groups(cortical_groups, subcortical_group_scores, betas)


# ── Pipeline ─────────────────────────────────────────────────────────────

def _run_pipeline(
    text: str,
    content_type: str,
    predictor: BrainPredictor,
    atlas: BrainAtlas,
    translator: Translator,
    sc_predictor=None,
    sc_atlas=None,
    sc_aggregator=None,
    mesh_meta_path: str | None = None,
) -> dict:
    # Cortical prediction
    preds, _segments = predictor.predict_text(text)
    aggregator = Aggregator(atlas)
    result = aggregator.process_prediction(preds)
    group_scores = translator.translate(result["regions"], result["region_zscores"])
    group_scores_dicts = [gs.to_dict() for gs in group_scores]

    # Build per-vertex group index array (20484 ints, 0-10)
    vertex_groups = _get_vertex_groups(atlas, translator)

    # Cortical vertex activations
    cortical_acts = result["vertex_activations"].tolist()

    # Subcortical prediction (if available)
    # Pass cortical predictor's model so subcortical doesn't re-load it
    cortical_tribe_model = getattr(predictor, 'model', None)
    sc_data = _run_subcortical(text, sc_predictor, sc_atlas, sc_aggregator, mesh_meta_path, cortical_model=cortical_tribe_model)

    subcortical_regions = []
    n_subcortical = 0
    group_scores_neuroscience = None

    if sc_data is not None:
        # Save cortical-only for neuroscience reblending
        cortical_only = copy.deepcopy(group_scores_dicts)

        # Merge subcortical group contributions into cortical group scores (conservative)
        group_scores_dicts = _merge_group_scores(group_scores_dicts, sc_data["group_scores"])

        # Compute neuroscience-balanced blend (equal model quality assumption)
        group_scores_neuroscience = _blend_groups(cortical_only, sc_data["group_scores"], NEUROSCIENCE_BETAS)

        # Build subcortical region response
        import json
        from pathlib import Path
        sc_map_path = Path(__file__).resolve().parent.parent.parent / "data" / "subcortical_cognitive_map.json"
        with open(sc_map_path) as f:
            sc_map = json.load(f)
        region_to_groups = sc_map.get("region_to_groups", {})

        for name, z in sc_data["region_zscores"].items():
            subcortical_regions.append({
                "name": name,
                "z_score": z,
                "group_ids": region_to_groups.get(name, []),
                "engaged": name in sc_data["engaged_regions"],
            })

        # Append subcortical mesh vertex activations to cortical
        if sc_data["mesh_vertex_activations"] is not None:
            sc_mesh_acts = sc_data["mesh_vertex_activations"]
            cortical_acts.extend(sc_mesh_acts.tolist())
            n_subcortical = len(sc_mesh_acts)

            # Extend vertex_groups with subcortical group indices
            # (these come from the mesh metadata _GROUPINDEX baked into the GLB)
            if mesh_meta_path:
                import json as json2
                with open(mesh_meta_path) as f:
                    meta = json2.load(f)
                for struct_name, info in meta.get("structures", {}).items():
                    gid = info["group_ids"][0] if info.get("group_ids") else 0
                    vertex_groups.extend([gid] * info["vertex_count"])

    narrative = generate_summary(group_scores, content_type=content_type)

    # --- Operator Readiness Dimensions ---
    gs_dict, sc_dict = extract_readiness_inputs(group_scores_dicts, subcortical_regions)
    raw_dims = detect_dimensions(gs_dict, sc_dict)

    _DIM_NAMES = {
        "procedural_automaticity": "Procedural Automaticity",
        "threat_detection": "Threat Detection & Calibration",
        "situational_awareness": "Situational Awareness",
        "strategic_decision": "Strategic Decision & Reflection",
        "analytical_synthesis": "Analytical Synthesis & Pattern Matching",
        "stress_resilience": "Stress Resilience",
    }
    operator_readiness = {}
    for dim_key, dim_data in raw_dims.items():
        operator_readiness[dim_key] = {
            "key": dim_key,
            "name": _DIM_NAMES[dim_key],
            **dim_data,
        }

    # --- Brain-derived completion type (Algorithm v3.2 integration) ---
    completion_type = classify_completion(gs_dict)

    return {
        "vertex_activations": cortical_acts,
        "vertex_groups": vertex_groups,
        "group_scores": group_scores_dicts,
        "group_scores_neuroscience": group_scores_neuroscience,
        "narrative_summary": narrative,
        "engaged_regions": result["engaged_regions"],
        "subcortical_regions": subcortical_regions,
        "n_cortical_vertices": 20484,
        "n_subcortical_vertices": n_subcortical,
        "operator_readiness": operator_readiness,
        "completion_type": completion_type,
    }


def _get_vertex_groups(atlas: BrainAtlas, translator: Translator) -> list[int]:
    """Map each of 20484 vertices to its capability group (0-10)."""
    n = 20484
    n_left = 10242
    groups = [0] * n

    for label_idx, label_name in enumerate(atlas.label_names):
        group_info = translator.get_group_for_region(label_name)
        if group_info is None:
            continue
        gid = group_info["id"]

        # Left hemisphere
        lh_mask = atlas.labels_lh == label_idx
        for vi in np.where(lh_mask)[0]:
            groups[vi] = gid

        # Right hemisphere
        rh_mask = atlas.labels_rh == label_idx
        for vi in np.where(rh_mask)[0]:
            groups[vi + n_left] = gid

    return groups


def _run_job(job_id: str, text: str, content_type: str,
             predictor: BrainPredictor, atlas: BrainAtlas, translator: Translator,
             sc_predictor=None, sc_atlas=None, sc_aggregator=None,
             mesh_meta_path: str | None = None):
    """Run prediction in a background thread."""
    try:
        _jobs[job_id]["status"] = "running"

        # Check cache first
        th = _text_hash(text)
        if th in _result_cache:
            logger.info("Cache hit for job %s", job_id)
            _jobs[job_id]["result"] = _result_cache[th]
            _jobs[job_id]["status"] = "complete"
            return

        result = _run_pipeline(
            text, content_type, predictor, atlas, translator,
            sc_predictor, sc_atlas, sc_aggregator, mesh_meta_path,
        )

        # Cache the result
        _result_cache[th] = result

        _jobs[job_id]["result"] = result
        _jobs[job_id]["status"] = "complete"
        logger.info("Job %s complete", job_id)

    except Exception as e:
        logger.exception("Job %s failed", job_id)
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/predict")
async def predict(
    request: Request,
    predictor: BrainPredictor = Depends(get_predictor),
    atlas: BrainAtlas = Depends(get_atlas),
    translator: Translator = Depends(get_translator),
    sc_predictor=Depends(get_subcortical_predictor),
    sc_atlas=Depends(get_subcortical_atlas),
    sc_aggregator=Depends(get_subcortical_aggregator),
):
    """Submit a prediction job. Returns job_id for polling, or full result if cached."""
    ct = request.headers.get("content-type", "")

    if "multipart" in ct or "form-urlencoded" in ct:
        form = await request.form()
        input_text = None
        content_type = str(form.get("content_type", "text module"))
        upload = form.get("file")
        if upload is not None and hasattr(upload, "read"):
            raw = await upload.read()
            input_text = raw.decode("utf-8", errors="replace")
        else:
            input_text = str(form.get("text", ""))
    else:
        body = await request.json()
        input_text = body.get("text", "")
        content_type = body.get("content_type", "text module")

    if not input_text or not input_text.strip():
        raise HTTPException(status_code=422, detail="Provide text or file.")

    # Check cache — return immediately if we have it
    th = _text_hash(input_text)
    if th in _result_cache:
        logger.info("Cache hit, returning immediately")
        return _result_cache[th]

    # Get mesh metadata path from settings
    from htb_brain.config import settings
    mesh_meta_path = settings.subcortical_mesh_meta or None

    # Create async job
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        "status": "queued",
        "created": time.time(),
        "text_preview": input_text[:80],
        "result": None,
        "error": None,
    }

    # Run in background thread (TRIBE v2 is CPU/GPU bound, not async)
    thread = threading.Thread(
        target=_run_job,
        args=(job_id, input_text, content_type, predictor, atlas, translator,
              sc_predictor, sc_atlas, sc_aggregator, mesh_meta_path),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Poll for job status. Returns result when complete."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _jobs[job_id]

    if job["status"] == "complete":
        result = job["result"]
        # Clean up old job after retrieval
        return {"status": "complete", **result}

    if job["status"] == "failed":
        return {"status": "failed", "error": job["error"]}

    elapsed = int(time.time() - job["created"])
    return {"status": job["status"], "elapsed_seconds": elapsed}
