"""POST /api/v1/predict/video — async video prediction pipeline."""

import hashlib
import logging
import os
import shutil
import tempfile
import threading
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from htb_brain.api.dependencies import (
    get_predictor, get_atlas, get_translator,
    get_subcortical_predictor, get_subcortical_atlas, get_subcortical_aggregator,
)
from htb_brain.api.schemas import GroupScoreResponse
from htb_brain.core.aggregator import Aggregator
from htb_brain.core.atlas import BrainAtlas
from htb_brain.core.predictor import BrainPredictor
from htb_brain.core.translator import Translator
from htb_brain.visualization.summary import generate_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["video"])

# Reuse the job store and helpers from predict module
from htb_brain.api.routes.predict import (
    _jobs, _result_cache, _get_vertex_groups,
    _run_subcortical as _run_subcortical_text,
    _merge_group_scores,
)

UPLOAD_DIR = "/workspace/tribe/cache/uploads"
MAX_VIDEO_SIZE_MB = 2000  # 2GB


def _video_hash(path: str) -> str:
    """Hash first 1MB + file size for fast cache key."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        chunk = f.read(1024 * 1024)
    return hashlib.sha256(chunk + str(size).encode()).hexdigest()[:16]


def _run_subcortical_video(video_path, sc_predictor, sc_atlas, sc_aggregator, mesh_meta_path):
    """Run subcortical prediction on video."""
    if sc_predictor is None:
        return None
    try:
        import numpy as np
        sc_preds, _ = sc_predictor.predict_video(video_path)
        sc_result = sc_aggregator.process_prediction(sc_preds)

        mesh_vertex_acts = None
        if mesh_meta_path:
            from htb_brain.visualization.subcortical_mesh_export import map_voxel_activations_to_mesh
            mean_act = np.mean(sc_preds, axis=0).astype(np.float32)
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
        logger.exception("Subcortical video prediction failed")
        return None


def _run_video_pipeline(
    video_path: str,
    content_type: str,
    predictor: BrainPredictor,
    atlas: BrainAtlas,
    translator: Translator,
    sc_predictor=None,
    sc_atlas=None,
    sc_aggregator=None,
    mesh_meta_path: str | None = None,
) -> dict:
    """Run TRIBE v2 on a video file (trimodal: visual + audio + speech)."""
    import numpy as np
    import json
    from pathlib import Path

    preds, _segments = predictor.predict_video(video_path)
    aggregator = Aggregator(atlas)
    result = aggregator.process_prediction(preds)
    group_scores = translator.translate(result["regions"], result["region_zscores"])
    group_scores_dicts = [gs.to_dict() for gs in group_scores]
    vertex_groups = _get_vertex_groups(atlas, translator)

    cortical_acts = result["vertex_activations"].tolist()

    # Subcortical
    sc_data = _run_subcortical_video(video_path, sc_predictor, sc_atlas, sc_aggregator, mesh_meta_path)

    subcortical_regions = []
    n_subcortical = 0

    if sc_data is not None:
        group_scores_dicts = _merge_group_scores(group_scores_dicts, sc_data["group_scores"])

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

        if sc_data["mesh_vertex_activations"] is not None:
            sc_mesh_acts = sc_data["mesh_vertex_activations"]
            cortical_acts.extend(sc_mesh_acts.tolist())
            n_subcortical = len(sc_mesh_acts)

            if mesh_meta_path:
                with open(mesh_meta_path) as f:
                    meta = json.load(f)
                for struct_name, info in meta.get("structures", {}).items():
                    gid = info["group_ids"][0] if info.get("group_ids") else 0
                    vertex_groups.extend([gid] * info["vertex_count"])

    narrative = generate_summary(group_scores, content_type=content_type)

    return {
        "vertex_activations": cortical_acts,
        "vertex_groups": vertex_groups,
        "group_scores": group_scores_dicts,
        "narrative_summary": narrative,
        "engaged_regions": result["engaged_regions"],
        "input_type": "video",
        "subcortical_regions": subcortical_regions,
        "n_cortical_vertices": 20484,
        "n_subcortical_vertices": n_subcortical,
    }


def _run_video_job(job_id: str, video_path: str, content_type: str,
                   predictor: BrainPredictor, atlas: BrainAtlas, translator: Translator,
                   sc_predictor=None, sc_atlas=None, sc_aggregator=None,
                   mesh_meta_path: str | None = None):
    """Run video prediction in a background thread."""
    try:
        _jobs[job_id]["status"] = "running"

        # Check cache
        vh = _video_hash(video_path)
        cache_key = f"video_{vh}"
        if cache_key in _result_cache:
            logger.info("Video cache hit for job %s", job_id)
            _jobs[job_id]["result"] = _result_cache[cache_key]
            _jobs[job_id]["status"] = "complete"
            return

        result = _run_video_pipeline(
            video_path, content_type, predictor, atlas, translator,
            sc_predictor, sc_atlas, sc_aggregator, mesh_meta_path,
        )

        _result_cache[cache_key] = result
        _jobs[job_id]["result"] = result
        _jobs[job_id]["status"] = "complete"
        logger.info("Video job %s complete", job_id)

    except Exception as e:
        logger.exception("Video job %s failed", job_id)
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
    finally:
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
                logger.info("Cleaned up %s", video_path)
        except Exception:
            pass


@router.post("/predict/video")
async def predict_video(
    file: UploadFile = File(...),
    content_type: str = Form("video"),
    predictor: BrainPredictor = Depends(get_predictor),
    atlas: BrainAtlas = Depends(get_atlas),
    translator: Translator = Depends(get_translator),
    sc_predictor=Depends(get_subcortical_predictor),
    sc_atlas=Depends(get_subcortical_atlas),
    sc_aggregator=Depends(get_subcortical_aggregator),
):
    """Upload a video file for brain engagement prediction.

    Supports .mp4, .webm, .avi, .mkv, .mov. Returns job_id for polling.
    """
    if not file.filename:
        raise HTTPException(422, "No filename provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".mp4", ".webm", ".avi", ".mkv", ".mov"):
        raise HTTPException(422, f"Unsupported video format: {ext}. Use .mp4, .webm, .avi, .mkv, .mov")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    video_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex[:12]}{ext}")

    size = 0
    with open(video_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_VIDEO_SIZE_MB * 1024 * 1024:
                os.remove(video_path)
                raise HTTPException(413, f"Video exceeds {MAX_VIDEO_SIZE_MB}MB limit")
            f.write(chunk)

    logger.info("Video uploaded: %s (%.1f MB)", file.filename, size / 1024 / 1024)

    from htb_brain.config import settings
    mesh_meta_path = settings.subcortical_mesh_meta or None

    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        "status": "queued",
        "created": time.time(),
        "text_preview": f"[VIDEO] {file.filename} ({size / 1024 / 1024:.1f} MB)",
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_video_job,
        args=(job_id, video_path, content_type, predictor, atlas, translator,
              sc_predictor, sc_atlas, sc_aggregator, mesh_meta_path),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "status": "queued", "filename": file.filename, "size_mb": round(size / 1024 / 1024, 1)}
