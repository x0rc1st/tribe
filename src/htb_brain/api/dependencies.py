"""Shared FastAPI dependencies — extract model, atlas, translator from app.state."""

from fastapi import Request

from htb_brain.core.predictor import BrainPredictor
from htb_brain.core.atlas import BrainAtlas
from htb_brain.core.translator import Translator


def get_predictor(request: Request) -> BrainPredictor:
    """Return the loaded BrainPredictor from app state."""
    return request.app.state.predictor


def get_atlas(request: Request) -> BrainAtlas:
    """Return the loaded BrainAtlas from app state."""
    return request.app.state.atlas


def get_translator(request: Request) -> Translator:
    """Return the loaded Translator from app state."""
    return request.app.state.translator


def get_subcortical_predictor(request: Request):
    """Return the SubcorticalPredictor if loaded, else None."""
    return getattr(request.app.state, "subcortical_predictor", None)


def get_subcortical_atlas(request: Request):
    """Return the SubcorticalAtlas if loaded, else None."""
    return getattr(request.app.state, "subcortical_atlas", None)


def get_subcortical_aggregator(request: Request):
    """Return the SubcorticalAggregator if loaded, else None."""
    return getattr(request.app.state, "subcortical_aggregator", None)
