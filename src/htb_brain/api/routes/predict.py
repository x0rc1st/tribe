"""POST /api/v1/predict — run TRIBE v2 prediction pipeline on text or uploaded file."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from htb_brain.api.dependencies import get_predictor, get_atlas, get_translator
from htb_brain.api.schemas import PredictTextRequest, PredictResponse, GroupScoreResponse
from htb_brain.core.aggregator import Aggregator
from htb_brain.core.atlas import BrainAtlas
from htb_brain.core.predictor import BrainPredictor
from htb_brain.core.translator import Translator
from htb_brain.visualization.summary import generate_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["predict"])


# ── helpers ──────────────────────────────────────────────────────────────

def _run_pipeline(
    text: str,
    content_type: str,
    predictor: BrainPredictor,
    atlas: BrainAtlas,
    translator: Translator,
) -> PredictResponse:
    """Shared pipeline used by both the JSON and form-data code paths."""

    # 1. Predict
    preds, _segments = predictor.predict_text(text)

    # 2. Aggregate
    aggregator = Aggregator(atlas)
    result = aggregator.process_prediction(preds)

    # 3. Translate
    group_scores = translator.translate(result["regions"], result["region_zscores"])

    # 4. Narrative
    narrative = generate_summary(group_scores, content_type=content_type)

    # 5. Build response
    vertex_activations = result["vertex_activations"].tolist()
    group_dicts = [gs.to_dict() for gs in group_scores]

    return PredictResponse(
        vertex_activations=vertex_activations,
        group_scores=[GroupScoreResponse(**gd) for gd in group_dicts],
        narrative_summary=narrative,
        engaged_regions=result["engaged_regions"],
    )


# ── Single endpoint that handles both JSON and form-data ─────────────────

@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="Predict brain engagement from text (JSON or multipart form)",
)
async def predict(
    request: Request,
    predictor: BrainPredictor = Depends(get_predictor),
    atlas: BrainAtlas = Depends(get_atlas),
    translator: Translator = Depends(get_translator),
):
    """Accept either JSON or multipart form-data."""
    ct = request.headers.get("content-type", "")

    if "multipart/form-data" in ct or "application/x-www-form-urlencoded" in ct:
        form = await request.form()
        input_text = None
        content_type = form.get("content_type", "text module")

        upload = form.get("file")
        if upload is not None and hasattr(upload, "read"):
            raw = await upload.read()
            input_text = raw.decode("utf-8", errors="replace")
        else:
            input_text = form.get("text")

        if not input_text or not str(input_text).strip():
            raise HTTPException(status_code=422, detail="Provide 'text' field or 'file' upload.")

        input_text = str(input_text)
    else:
        body = await request.json()
        input_text = body.get("text", "")
        content_type = body.get("content_type", "text module")
        if not input_text.strip():
            raise HTTPException(status_code=422, detail="Text field must not be empty.")

    try:
        return _run_pipeline(input_text, content_type, predictor, atlas, translator)
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
