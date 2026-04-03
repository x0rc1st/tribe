"""FastAPI application factory for HTB Brain Engagement Service (Phase 4)."""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

# Ensure project src is on the path
sys.path.insert(0, "/workspace/tribe/src")

from htb_brain.config import settings  # noqa: E402

logger = logging.getLogger("htb_brain.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load TRIBE v2 model, Destrieux atlas, and cognitive translator on startup."""

    # Propagate HF token if configured via environment
    hf_token = os.environ.get("HF_TOKEN") or getattr(settings, "hf_token", None)
    if hf_token:
        os.environ["HF_TOKEN"] = hf_token
        logger.info("HF_TOKEN set from environment / settings.")

    # --- Load BrainPredictor ---
    from htb_brain.core.predictor import BrainPredictor

    predictor = BrainPredictor(
        model_repo=settings.model_repo,
        cache_dir=settings.model_cache_dir,
        device=settings.device,
    )
    predictor.load()
    app.state.predictor = predictor
    logger.info("BrainPredictor ready.")

    # --- Load BrainAtlas ---
    from htb_brain.core.atlas import BrainAtlas

    atlas = BrainAtlas()
    atlas.load()
    app.state.atlas = atlas
    logger.info("BrainAtlas ready.")

    # --- Load Translator ---
    from htb_brain.core.translator import Translator

    cognitive_map_path = Path("/workspace/tribe/src/htb_brain/data/cognitive_map.json")
    translator = Translator(cognitive_map_path)
    translator.load()
    app.state.translator = translator
    logger.info("Translator ready.")

    yield  # Application runs

    # Cleanup (if needed in future)
    logger.info("Shutting down HTB Brain service.")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""

    app = FastAPI(
        title="HTB Brain Engagement Service",
        description="TRIBE v2 prediction pipeline with 3D brain viewer UI",
        version="0.4.0",
        lifespan=lifespan,
    )

    # --- CORS (permissive for development) ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Static files ---
    static_dir = Path(__file__).resolve().parent.parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # --- Routes ---
    from htb_brain.api.routes.predict import router as predict_router
    from htb_brain.api.routes.health import router as health_router
    from htb_brain.api.routes.aggregate import router as aggregate_router

    app.include_router(predict_router)
    app.include_router(health_router)
    app.include_router(aggregate_router)

    # --- Root redirect ---
    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/static/brain_viewer/index.html")

    return app


app = create_app()
