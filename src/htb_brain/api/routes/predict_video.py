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

from htb_brain.api.dependencies import get_predictor, get_atlas, get_translator
from htb_brain.api.schemas import GroupScoreResponse
from htb_brain.core.aggregator import Aggregator
from htb_brain.core.atlas import BrainAtlas
from htb_brain.core.predictor import BrainPredictor
from htb_brain.core.translator import Translator
from htb_brain.visualization.summary import generate_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["video"])

# Reuse the job store and vertex_groups helper from predict module
from htb_brain.api.routes.predict import _jobs, _result_cache, _get_vertex_groups

UPLOAD_DIR = "/workspace/tribe/cache/uploads"
MAX_VIDEO_SIZE_MB = 500


def _video_hash(path: str) -> str:
    """Hash first 1MB + file size for fast cache key."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        chunk = f.read(1024 * 1024)
    return hashlib.sha256(chunk + str(size).encode()).hexdigest()[:16]


def _run_video_pipeline(
    video_path: str,
    content_type: str,
    predictor: BrainPredictor,
    atlas: BrainAtlas,
    translator: Translator,
) -> dict:
    """Run TRIBE v2 on a video file (trimodal: visual + audio + speech)."""
    preds, _segments = predictor.predict_video(video_path)
    aggregator = Aggregator(atlas)
    result = aggregator.process_prediction(preds)
    group_scores = translator.translate(result["regions"], result["region_zscores"])
    narrative = generate_summary(group_scores, content_type=content_type)
    vertex_groups = _get_vertex_groups(atlas, translator)

    return {
        "vertex_activations": result["vertex_activations"].tolist(),
        "vertex_groups": vertex_groups,
        "group_scores": [gs.to_dict() for gs in group_scores],
        "narrative_summary": narrative,
        "engaged_regions": result["engaged_regions"],
        "input_type": "video",
    }


def _run_video_job(job_id: str, video_path: str, content_type: str,
                   predictor: BrainPredictor, atlas: BrainAtlas, translator: Translator):
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

        result = _run_video_pipeline(video_path, content_type, predictor, atlas, translator)

        _result_cache[cache_key] = result
        _jobs[job_id]["result"] = result
        _jobs[job_id]["status"] = "complete"
        logger.info("Video job %s complete", job_id)

    except Exception as e:
        logger.exception("Video job %s failed", job_id)
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
    finally:
        # Clean up uploaded file after processing
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
):
    """Upload a video file for brain engagement prediction.

    Supports .mp4, .webm, .avi, .mkv, .mov. Returns job_id for polling.
    Video processing takes 5-10 minutes depending on duration.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(422, "No filename provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".mp4", ".webm", ".avi", ".mkv", ".mov"):
        raise HTTPException(422, f"Unsupported video format: {ext}. Use .mp4, .webm, .avi, .mkv, .mov")

    # Save upload to disk
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

    # Create async job
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
        args=(job_id, video_path, content_type, predictor, atlas, translator),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "status": "queued", "filename": file.filename, "size_mb": round(size / 1024 / 1024, 1)}
