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

    # --- Load Subcortical model (optional — requires trained checkpoint) ---
    app.state.subcortical_predictor = None
    app.state.subcortical_atlas = None
    app.state.subcortical_aggregator = None

    # Auto-detect subcortical checkpoint
    sc_ckpt_dir = settings.subcortical_checkpoint_dir
    if not sc_ckpt_dir:
        from pathlib import Path as _P
        _default = _P("/workspace/tribe/subcortical_training/results/best.ckpt")
        if _default.exists():
            sc_ckpt_dir = str(_default.parent)
            logger.info("Auto-detected subcortical checkpoint: %s", sc_ckpt_dir)

    if sc_ckpt_dir:
        try:
            from htb_brain.core.subcortical_predictor import SubcorticalPredictor
            from htb_brain.core.subcortical_atlas import SubcorticalAtlas
            from htb_brain.core.subcortical_aggregator import SubcorticalAggregator

            sc_predictor = SubcorticalPredictor(
                checkpoint_dir=sc_ckpt_dir,
                cache_dir=settings.model_cache_dir,
                device=settings.device,
            )
            sc_predictor.load()
            app.state.subcortical_predictor = sc_predictor

            sc_atlas = SubcorticalAtlas()
            sc_atlas.load()
            app.state.subcortical_atlas = sc_atlas

            sc_aggregator = SubcorticalAggregator(sc_atlas)
            app.state.subcortical_aggregator = sc_aggregator

            logger.info("Subcortical model ready (%d voxels).", sc_predictor.n_outputs)
        except Exception:
            logger.exception("Failed to load subcortical model — cortical-only mode.")

    # --- Initialize Operator Profile Store ---
    from htb_brain.core.profile_store import ProfileStore
    from pathlib import Path as _ProfilePath

    profile_db = _ProfilePath(settings.model_cache_dir).parent / "data" / "operator_profiles.db"
    profile_db.parent.mkdir(parents=True, exist_ok=True)
    app.state.profile_store = ProfileStore(profile_db)
    logger.info("ProfileStore ready at %s", profile_db)

    # --- Initialize Mastery Store (Algorithm v3.2 + ORI) ---
    from htb_brain.core.mastery_store import MasteryStore

    mastery_db = _ProfilePath(settings.model_cache_dir).parent / "data" / "mastery.db"
    mastery_db.parent.mkdir(parents=True, exist_ok=True)
    app.state.mastery_store = MasteryStore(mastery_db)
    logger.info("MasteryStore ready at %s", mastery_db)

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
    from htb_brain.api.routes.predict_video import router as video_router
    from htb_brain.api.routes.health import router as health_router
    from htb_brain.api.routes.aggregate import router as aggregate_router
    from htb_brain.api.routes.profile import router as profile_router
    from htb_brain.api.routes.mastery import router as mastery_router
    from htb_brain.api.routes.classify import router as classify_router

    app.include_router(predict_router)
    app.include_router(video_router)
    app.include_router(health_router)
    app.include_router(aggregate_router)
    app.include_router(profile_router)
    app.include_router(mastery_router)
    app.include_router(classify_router)

    # --- Root redirect ---
    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/static/brain_viewer/index.html")

    return app


app = create_app()
