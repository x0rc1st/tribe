"""POST /api/v1/predict — async job-based prediction pipeline."""

import asyncio
import hashlib
import logging
import threading
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from htb_brain.api.dependencies import get_predictor, get_atlas, get_translator
from htb_brain.api.schemas import PredictResponse, GroupScoreResponse
from htb_brain.core.aggregator import Aggregator
from htb_brain.core.atlas import BrainAtlas
from htb_brain.core.predictor import BrainPredictor
from htb_brain.core.translator import Translator
from htb_brain.visualization.summary import generate_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["predict"])

# ── Job store (in-memory) ────────────────────────────────────────────────

_jobs: dict[str, dict[str, Any]] = {}
_result_cache: dict[str, dict] = {}  # text_hash -> result dict


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode()).hexdigest()[:16]


# ── Pipeline ─────────────────────────────────────────────────────────────

def _run_pipeline(
    text: str,
    content_type: str,
    predictor: BrainPredictor,
    atlas: BrainAtlas,
    translator: Translator,
) -> dict:
    preds, _segments = predictor.predict_text(text)
    aggregator = Aggregator(atlas)
    result = aggregator.process_prediction(preds)
    group_scores = translator.translate(result["regions"], result["region_zscores"])
    narrative = generate_summary(group_scores, content_type=content_type)

    return {
        "vertex_activations": result["vertex_activations"].tolist(),
        "group_scores": [gs.to_dict() for gs in group_scores],
        "narrative_summary": narrative,
        "engaged_regions": result["engaged_regions"],
    }


def _run_job(job_id: str, text: str, content_type: str,
             predictor: BrainPredictor, atlas: BrainAtlas, translator: Translator):
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

        result = _run_pipeline(text, content_type, predictor, atlas, translator)

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
        args=(job_id, input_text, content_type, predictor, atlas, translator),
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
