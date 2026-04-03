"""Aggregation — per-unit and cross-unit activation processing."""

import logging

import numpy as np
from scipy import stats

from htb_brain.core.atlas import BrainAtlas, RegionActivation, N_VERTICES

logger = logging.getLogger(__name__)


class Aggregator:
    """Processes raw TRIBE v2 predictions into normalized region scores."""

    def __init__(self, atlas: BrainAtlas, threshold_percentile: float = 75.0, bilateral_collapse: bool = True):
        self.atlas = atlas
        self.threshold_percentile = threshold_percentile
        self.bilateral_collapse = bilateral_collapse

    def process_prediction(
        self, preds: np.ndarray
    ) -> dict:
        """Process a single prediction into region scores.

        Args:
            preds: (n_timesteps, 20484) raw TRIBE v2 output

        Returns:
            dict with:
                - vertex_activations: (20484,) mean activation per vertex, normalized 0-1
                - regions: dict[str, RegionActivation] named region scores
                - region_zscores: dict[str, float] z-scored region activations
                - engaged_regions: list[str] regions above threshold
                - threshold_value: float the z-score cutoff used
        """
        assert preds.ndim == 2 and preds.shape[1] == N_VERTICES, (
            f"Expected (n, {N_VERTICES}), got {preds.shape}"
        )

        # Step 1: Mean across timesteps
        mean_activation = np.mean(preds, axis=0)  # (20484,)

        # Step 2: Map to named regions
        regions = self.atlas.map_activations(mean_activation, bilateral_collapse=self.bilateral_collapse)

        # Step 3: Z-score region activations
        activations = np.array([r.activation for r in regions.values()])
        z_scores = stats.zscore(activations) if len(activations) > 1 else np.zeros_like(activations)
        region_zscores = {name: float(z) for name, z in zip(regions.keys(), z_scores)}

        # Step 4: Threshold — top N% are "engaged"
        threshold = float(np.percentile(z_scores, self.threshold_percentile))
        engaged = [name for name, z in region_zscores.items() if z >= threshold]

        # Step 5: Sparsify vertex activations — only top 25% glow, rest zero
        p75 = np.percentile(mean_activation, 75)
        p99 = np.percentile(mean_activation, 99)
        sparse = np.clip((mean_activation - p75) / (p99 - p75 + 1e-8), 0, 1)
        normalized_vertices = np.power(sparse, 1.5)  # contrast boost

        logger.info(
            "Processed: %d regions, %d engaged (threshold z=%.2f at p%d)",
            len(regions),
            len(engaged),
            threshold,
            int(self.threshold_percentile),
        )

        return {
            "vertex_activations": normalized_vertices.astype(np.float32),
            "regions": regions,
            "region_zscores": region_zscores,
            "engaged_regions": engaged,
            "threshold_value": threshold,
        }

    def aggregate_units(self, unit_results: list[dict]) -> dict:
        """Aggregate results across multiple learning units.

        Args:
            unit_results: list of process_prediction() outputs

        Returns:
            dict with cumulative and comparative data
        """
        if not unit_results:
            raise ValueError("No unit results to aggregate")

        # Stack vertex activations across units
        all_vertices = np.stack([r["vertex_activations"] for r in unit_results])  # (n_units, 20484)
        cumulative_vertices = np.mean(all_vertices, axis=0)

        # Aggregate region z-scores
        all_region_names = set()
        for r in unit_results:
            all_region_names.update(r["region_zscores"].keys())

        cumulative_zscores = {}
        variance_zscores = {}
        for name in all_region_names:
            scores = [r["region_zscores"].get(name, 0.0) for r in unit_results]
            cumulative_zscores[name] = float(np.mean(scores))
            variance_zscores[name] = float(np.var(scores))

        # Find differentially engaged regions (high variance = different across units)
        threshold = float(np.percentile(list(cumulative_zscores.values()), self.threshold_percentile))
        engaged = [name for name, z in cumulative_zscores.items() if z >= threshold]

        logger.info(
            "Aggregated %d units: %d total regions, %d engaged",
            len(unit_results),
            len(all_region_names),
            len(engaged),
        )

        return {
            "vertex_activations": cumulative_vertices.astype(np.float32),
            "cumulative_zscores": cumulative_zscores,
            "variance_zscores": variance_zscores,
            "engaged_regions": engaged,
            "n_units": len(unit_results),
            "per_unit_zscores": [r["region_zscores"] for r in unit_results],
        }
