"""Subcortical aggregation — processes subcortical voxel predictions into region scores."""

import json
import logging
from pathlib import Path

import numpy as np
from scipy import stats

from htb_brain.core.subcortical_atlas import SubcorticalAtlas, SubcorticalRegion

logger = logging.getLogger(__name__)

# Default path to subcortical cognitive map
_DEFAULT_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "subcortical_cognitive_map.json"


class SubcorticalAggregator:
    """Processes raw subcortical model predictions into region and group scores.

    This is the subcortical counterpart of Aggregator + Translator, combined
    into one class because the subcortical pipeline is simpler (fewer regions,
    direct region→group mapping).
    """

    def __init__(
        self,
        atlas: SubcorticalAtlas,
        cognitive_map_path: str | Path = _DEFAULT_MAP_PATH,
        threshold_percentile: float = 75.0,
        bilateral_collapse: bool = True,
    ):
        self.atlas = atlas
        self.threshold_percentile = threshold_percentile
        self.bilateral_collapse = bilateral_collapse
        self._region_to_groups: dict[str, list[int]] = {}
        self._group_info: dict[int, dict] = {}

        # Load cognitive map
        with open(cognitive_map_path) as f:
            data = json.load(f)
        self._region_to_groups = data["region_to_groups"]
        for g in data["groups"]:
            self._group_info[g["id"]] = g

    def process_prediction(self, preds: np.ndarray) -> dict:
        """Process subcortical predictions into region and group scores.

        Args:
            preds: (n_timesteps, n_subcortical_voxels) raw model output

        Returns:
            dict with:
                - regions: dict[str, SubcorticalRegion]
                - region_zscores: dict[str, float]
                - engaged_regions: list[str]
                - group_scores: dict[int, float] (group_id -> mean z-score)
                - threshold_value: float
        """
        assert preds.ndim == 2 and preds.shape[1] == self.atlas.n_voxels, (
            f"Expected (n, {self.atlas.n_voxels}), got {preds.shape}"
        )

        # Step 1: Average across timesteps
        mean_activation = np.mean(preds, axis=0)

        # Step 2: Map to named regions
        regions = self.atlas.map_activations(
            mean_activation, bilateral_collapse=self.bilateral_collapse
        )

        # Step 3: Z-score region activations
        activations = np.array([r.activation for r in regions.values()])
        z_scores = stats.zscore(activations) if len(activations) > 1 else np.zeros_like(activations)
        region_zscores = {name: float(z) for name, z in zip(regions.keys(), z_scores)}

        # Step 4: Threshold
        threshold = float(np.percentile(z_scores, self.threshold_percentile))
        engaged = [name for name, z in region_zscores.items() if z >= threshold]

        # Step 5: Compute group-level scores from subcortical contributions
        group_scores = {}
        for group_id, group_info in self._group_info.items():
            member_z = []
            for region_name in group_info.get("subcortical_regions", []):
                if region_name in region_zscores:
                    member_z.append(region_zscores[region_name])
            group_scores[group_id] = float(np.mean(member_z)) if member_z else 0.0

        logger.info(
            "Subcortical: %d regions, %d engaged, %d groups scored",
            len(regions), len(engaged), len(group_scores),
        )

        return {
            "regions": regions,
            "region_zscores": region_zscores,
            "engaged_regions": engaged,
            "group_scores": group_scores,
            "threshold_value": threshold,
        }
