"""POST /api/v1/predict/claude — Claude-as-TRIBE prediction path.

A third prediction mode (alongside TRIBE conservative and TRIBE neuroscience
blending) that bypasses the real TRIBE model entirely and uses Claude to
estimate per-region z-scores from the module text. Those z-scores are then
fed through the same downstream pipeline that TRIBE's output goes through
(Translator → blend → narrative → readiness → completion type), so the
response shape and glass-brain render are byte-identical.

The route follows the same async-job pattern as `/api/v1/predict` and reuses
its `_jobs` store + `/api/v1/jobs/{job_id}` polling endpoint, so the frontend
can treat Claude and TRIBE jobs uniformly.
"""

from __future__ import annotations

import copy
import json
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request

from htb_brain.api.dependencies import get_atlas, get_translator
from htb_brain.api.routes.predict import (
    _jobs,
    _result_cache,
    _text_hash,
    _get_evidence_weights,
    _get_vertex_groups,
    _blend_groups,
    _merge_group_scores,
    _build_composition,
    NEUROSCIENCE_BETAS,
)
from htb_brain.core.atlas import BrainAtlas, N_VERTICES, N_LEFT
from htb_brain.core.translator import Translator
from htb_brain.core.completion_classifier import (
    classify_completion,
    classify_completion_detailed,
)
from htb_brain.core.operator_readiness import detect_dimensions, extract_readiness_inputs
from htb_brain.visualization.summary import generate_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["predict-claude"])


# ── ClaudePredictor singleton ────────────────────────────────────────────

_predictor_singleton = None
_predictor_lock = threading.Lock()


def _get_claude_predictor():
    """Lazy-instantiate a module-level ClaudePredictor."""
    global _predictor_singleton
    if _predictor_singleton is None:
        with _predictor_lock:
            if _predictor_singleton is None:
                from htb_brain.config import settings
                from htb_brain.core.claude_predictor import ClaudePredictor

                if not settings.anthropic_api_key:
                    raise HTTPException(
                        status_code=503,
                        detail=(
                            "Claude predictor requires an API key. "
                            "Set HTB_BRAIN_ANTHROPIC_API_KEY or ANTHROPIC_API_KEY."
                        ),
                    )
                _predictor_singleton = ClaudePredictor(
                    api_key=settings.anthropic_api_key,
                    model=settings.claude_model,
                    max_tokens=settings.claude_max_tokens,
                    thinking_budget=settings.claude_thinking_budget,
                )
    return _predictor_singleton


# ── Back-projection helpers ──────────────────────────────────────────────

def _cortical_vertex_activations(
    atlas: BrainAtlas, cortical_z: dict[str, float]
) -> np.ndarray:
    """Project per-region z-scores onto the 20,484 cortical vertices, then
    normalize to 0-1 across all vertices (matching Aggregator's output shape)."""
    vertex_vals = np.zeros(N_VERTICES, dtype=np.float32)

    for label_idx, label_name in enumerate(atlas.label_names):
        z = cortical_z.get(label_name)
        if z is None:
            continue
        lh_indices = np.where(atlas.labels_lh == label_idx)[0]
        rh_indices = np.where(atlas.labels_rh == label_idx)[0] + N_LEFT
        if len(lh_indices) > 0:
            vertex_vals[lh_indices] = z
        if len(rh_indices) > 0:
            vertex_vals[rh_indices] = z

    vmin, vmax = vertex_vals.min(), vertex_vals.max()
    if vmax - vmin > 0:
        return (vertex_vals - vmin) / (vmax - vmin)
    return np.zeros_like(vertex_vals)


def _subcortical_group_scores(subcortical_z: dict[str, float]) -> dict[int, float]:
    """Mean-of-member-structures per group. Matches SubcorticalAggregator output."""
    sc_map_path = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "subcortical_cognitive_map.json"
    )
    with open(sc_map_path) as f:
        sc_map = json.load(f)

    group_scores: dict[int, float] = {}
    for g in sc_map.get("groups", []):
        members = g.get("subcortical_regions", [])
        member_z = [subcortical_z[m] for m in members if m in subcortical_z]
        group_scores[g["id"]] = float(np.mean(member_z)) if member_z else 0.0
    return group_scores


def _build_subcortical_regions_payload(
    subcortical_z: dict[str, float], engaged_threshold: float
) -> list[dict]:
    """Build the `subcortical_regions` list matching the TRIBE response shape."""
    sc_map_path = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "subcortical_cognitive_map.json"
    )
    with open(sc_map_path) as f:
        sc_map = json.load(f)
    region_to_groups = sc_map.get("region_to_groups", {})

    return [
        {
            "name": name,
            "z_score": z,
            "group_ids": region_to_groups.get(name, []),
            "engaged": z >= engaged_threshold,
        }
        for name, z in subcortical_z.items()
    ]


def _subcortical_mesh_activations(
    subcortical_z: dict[str, float], mesh_meta_path: str
) -> tuple[np.ndarray, list[int]]:
    """Build (mesh_vertex_activations, vertex_group_indices) for the combined mesh.

    Iterates structures in the order they appear in the meta JSON, assigns every
    vertex in the structure's range the structure's normalized z-score, and
    captures the primary group index per vertex.
    """
    with open(mesh_meta_path) as f:
        meta = json.load(f)

    structures = meta.get("structures", {})
    z_values = np.array(list(subcortical_z.values()))
    zmin, zmax = z_values.min(), z_values.max()

    def normalize(z: float) -> float:
        if zmax - zmin > 0:
            return float((z - zmin) / (zmax - zmin))
        return 0.0

    activations: list[float] = []
    groups: list[int] = []
    for struct_name, info in structures.items():
        if not isinstance(info, dict):
            continue
        count = info.get("vertex_count", 0)
        if count <= 0:
            continue
        z = subcortical_z.get(struct_name, 0.0)
        activations.extend([normalize(z)] * count)
        gid = info["group_ids"][0] if info.get("group_ids") else 0
        groups.extend([gid] * count)

    return np.array(activations, dtype=np.float32), groups


# ── Pipeline ─────────────────────────────────────────────────────────────

def _postprocess_claude_output(
    cortical_z: dict[str, float],
    subcortical_z: dict[str, float],
    reasoning: str,
    content_type: str,
    atlas: BrainAtlas,
    translator: Translator,
    mesh_meta_path: str | None,
) -> dict:
    """Take Claude's raw per-region z-scores and run the same downstream
    pipeline TRIBE output goes through — back-projection to vertex activations,
    Translator → conservative blend + neuroscience blend, subcortical mesh
    mapping, narrative generation, operator-readiness detection, completion-
    type classification. Returns the same dict shape as `_run_pipeline` in
    predict.py, so the frontend viewer cannot tell the two engines apart.

    Separated from the live-API call so the batch-ingest pipeline (which
    fetches pre-computed Claude outputs from the Message Batches API) can
    reuse exactly the same downstream logic without double-charging for
    inference.
    """
    # --- Vertex activations (cortical) ---
    cortical_vertex_acts = _cortical_vertex_activations(atlas, cortical_z)

    # --- Translate cortical → group scores ---
    # Translator.translate only reads region_zscores; it tolerates an empty
    # `regions` dict — we pass {} to stay honest that Claude didn't produce
    # RegionActivation objects.
    group_scores = translator.translate({}, cortical_z)
    group_scores_dicts = [gs.to_dict() for gs in group_scores]

    # --- Engaged regions (top-25% z-score threshold, same as TRIBE Aggregator) ---
    z_array = np.array(list(cortical_z.values()))
    threshold_z = float(np.percentile(z_array, 75.0))
    engaged_regions = [name for name, z in cortical_z.items() if z >= threshold_z]

    # --- Vertex group indices ---
    vertex_groups = _get_vertex_groups(atlas, translator)

    # --- Subcortical path ---
    cortical_only = copy.deepcopy(group_scores_dicts)
    sc_group_scores = _subcortical_group_scores(subcortical_z)

    # Conservative blend (using per-group evidence_weight × subcortical_reliability)
    group_scores_dicts = _merge_group_scores(group_scores_dicts, sc_group_scores)

    # Neuroscience blend (equal-quality assumption)
    group_scores_neuroscience = _blend_groups(
        cortical_only, sc_group_scores, NEUROSCIENCE_BETAS
    )

    # Subcortical region payload (7 structures)
    sc_z_array = np.array(list(subcortical_z.values()))
    sc_engaged_threshold = float(np.percentile(sc_z_array, 75.0))
    subcortical_regions = _build_subcortical_regions_payload(
        subcortical_z, sc_engaged_threshold
    )

    # Subcortical mesh activations (for combined GLB render)
    cortical_acts_list: list[float] = cortical_vertex_acts.tolist()
    n_subcortical = 0
    if mesh_meta_path and Path(mesh_meta_path).exists():
        sc_mesh_acts, sc_mesh_groups = _subcortical_mesh_activations(
            subcortical_z, mesh_meta_path
        )
        cortical_acts_list.extend(sc_mesh_acts.tolist())
        vertex_groups.extend(sc_mesh_groups)
        n_subcortical = len(sc_mesh_acts)

    # --- Narrative, readiness, completion type ---
    narrative = generate_summary(group_scores, content_type=content_type)
    if reasoning:
        narrative = (
            f"_Claude's register analysis: {reasoning.strip()}_\n\n" + narrative
        )

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
    operator_readiness = {
        dim_key: {"key": dim_key, "name": _DIM_NAMES[dim_key], **dim_data}
        for dim_key, dim_data in raw_dims.items()
    }

    completion_type = classify_completion(gs_dict)
    group_names = {gs["id"]: gs["name"] for gs in group_scores_dicts}
    completion_breakdown = {
        str(n): classify_completion_detailed(gs_dict, top_n=n, group_names=group_names)
        for n in (3, 4, 5)
    }
    completion_composition = _build_composition(gs_dict, group_scores_dicts)

    return {
        "vertex_activations": cortical_acts_list,
        "vertex_groups": vertex_groups,
        "group_scores": group_scores_dicts,
        "group_scores_neuroscience": group_scores_neuroscience,
        "narrative_summary": narrative,
        "engaged_regions": engaged_regions,
        "subcortical_regions": subcortical_regions,
        "n_cortical_vertices": 20484,
        "n_subcortical_vertices": n_subcortical,
        "operator_readiness": operator_readiness,
        "completion_type": completion_type,
        "completion_breakdown": completion_breakdown,
        "completion_composition": completion_composition,
        "prediction_engine": "claude",
    }


def _run_claude_pipeline(
    text: str,
    content_type: str,
    atlas: BrainAtlas,
    translator: Translator,
    mesh_meta_path: str | None,
) -> dict:
    """Full live-API pipeline: call Claude, then post-process."""
    predictor = _get_claude_predictor()
    pred = predictor.predict(text)
    return _postprocess_claude_output(
        cortical_z=pred["cortical_region_zscores"],
        subcortical_z=pred["subcortical_region_zscores"],
        reasoning=pred.get("reasoning", ""),
        content_type=content_type,
        atlas=atlas,
        translator=translator,
        mesh_meta_path=mesh_meta_path,
    )


def _run_claude_job(
    job_id: str,
    text: str,
    content_type: str,
    atlas: BrainAtlas,
    translator: Translator,
    mesh_meta_path: str | None,
):
    """Run the Claude pipeline in a background thread; mirrors _run_job (TRIBE)."""
    try:
        _jobs[job_id]["status"] = "running"

        th = _claude_cache_key(text)
        if th in _result_cache:
            logger.info("Claude cache hit for job %s", job_id)
            _jobs[job_id]["result"] = _result_cache[th]
            _jobs[job_id]["status"] = "complete"
            return

        result = _run_claude_pipeline(text, content_type, atlas, translator, mesh_meta_path)
        _result_cache[th] = result
        _jobs[job_id]["result"] = result
        _jobs[job_id]["status"] = "complete"
        logger.info("Claude job %s complete", job_id)
    except Exception as e:
        logger.exception("Claude job %s failed", job_id)
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)


def _claude_cache_key(text: str) -> str:
    """Namespace Claude cache keys so they don't collide with TRIBE keys for the same text."""
    return "claude:" + _text_hash(text)


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/predict/claude")
async def predict_claude(
    request: Request,
    atlas: BrainAtlas = Depends(get_atlas),
    translator: Translator = Depends(get_translator),
):
    """Submit a Claude-based prediction job. Returns `{job_id, status}` or the
    cached result immediately if we've seen this text before.

    The response shape is byte-identical to `/api/v1/predict` so the frontend
    viewer can treat the two engines uniformly — the only difference is the
    `prediction_engine: "claude"` tag in the result.
    """
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

    # Cache hit → return immediately
    th = _claude_cache_key(input_text)
    if th in _result_cache:
        logger.info("Claude cache hit, returning immediately")
        return _result_cache[th]

    # Verify API key is configured before queueing a job that will fail
    _get_claude_predictor()  # raises HTTPException(503) if not configured

    from htb_brain.config import settings
    mesh_meta_path = settings.subcortical_mesh_meta or None

    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        "status": "queued",
        "created": time.time(),
        "text_preview": input_text[:80],
        "result": None,
        "error": None,
        "engine": "claude",
    }

    thread = threading.Thread(
        target=_run_claude_job,
        args=(job_id, input_text, content_type, atlas, translator, mesh_meta_path),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "status": "queued", "engine": "claude"}


@router.post("/predict/claude/ingest")
async def claude_ingest_result(
    payload: dict[str, Any],
    atlas: BrainAtlas = Depends(get_atlas),
    translator: Translator = Depends(get_translator),
):
    """Ingest a pre-computed Claude prediction into the cache.

    Used by `scripts/batch_ingest_claude.py` to prepopulate the cache from a
    Message Batches API run (50 % cheaper than live). The batch script fetches
    raw Claude outputs from the Anthropic API and posts each one here — the
    server runs the same downstream pipeline it would for a live call and
    caches the resulting PredictResponse so the viewer toggle finds it
    instantly.

    Body::

        {
            "text": "<original module text>",
            "cortical_region_zscores": {"G_front_sup": 0.8, ...},
            "subcortical_region_zscores": {"Hippocampus": 1.5, ...},
            "reasoning": "<optional short analysis>",
            "content_type": "text module"
        }
    """
    text = payload.get("text", "")
    cortical_z = payload.get("cortical_region_zscores")
    subcortical_z = payload.get("subcortical_region_zscores")
    if not text or not cortical_z or not subcortical_z:
        raise HTTPException(
            status_code=422,
            detail=(
                "Payload must include `text`, `cortical_region_zscores`, "
                "and `subcortical_region_zscores`."
            ),
        )

    from htb_brain.config import settings
    mesh_meta_path = settings.subcortical_mesh_meta or None

    try:
        result = _postprocess_claude_output(
            cortical_z=cortical_z,
            subcortical_z=subcortical_z,
            reasoning=payload.get("reasoning", ""),
            content_type=payload.get("content_type", "text module"),
            atlas=atlas,
            translator=translator,
            mesh_meta_path=mesh_meta_path,
        )
    except Exception as e:
        logger.exception("Claude ingest post-processing failed")
        raise HTTPException(status_code=500, detail=f"Post-processing failed: {e}")

    th = _claude_cache_key(text)
    _result_cache[th] = result
    return {"cached_key": th, "ok": True, "engine": "claude"}
