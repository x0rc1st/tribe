"""Destrieux atlas — maps 20,484 fsaverage5 vertices to named brain regions."""

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

N_VERTICES = 20484
N_LEFT = 10242
EXCLUDED_LABELS = {"Unknown", "Medial_wall"}


@dataclass
class RegionActivation:
    name: str
    hemisphere: str  # "L", "R", or "bilateral"
    activation: float
    vertex_indices: np.ndarray


class BrainAtlas:
    """Loads Destrieux atlas and maps vertex activations to named regions."""

    def __init__(self):
        self.labels_lh: np.ndarray | None = None
        self.labels_rh: np.ndarray | None = None
        self.label_names: list[str] = []
        self._loaded = False

    def load(self):
        """Load Destrieux atlas labels from nilearn."""
        from nilearn import datasets

        destrieux = datasets.fetch_atlas_surf_destrieux()
        self.labels_lh = destrieux["map_left"]
        self.labels_rh = destrieux["map_right"]
        self.label_names = [l.decode() if isinstance(l, bytes) else l for l in destrieux["labels"]]

        total = len(self.labels_lh) + len(self.labels_rh)
        logger.info(
            "Destrieux atlas loaded: %d labels, %d total vertices (L=%d R=%d)",
            len(self.label_names),
            total,
            len(self.labels_lh),
            len(self.labels_rh),
        )
        assert total == N_VERTICES, f"Expected {N_VERTICES} vertices, got {total}"
        self._loaded = True

    def map_activations(
        self, vertex_activations: np.ndarray, bilateral_collapse: bool = True
    ) -> dict[str, RegionActivation]:
        """Map per-vertex activations to named region activations.

        Args:
            vertex_activations: (20484,) mean activation per vertex
            bilateral_collapse: if True, average L+R hemispheres for same region

        Returns:
            dict of region_name -> RegionActivation
        """
        assert self._loaded, "Atlas not loaded. Call load() first."
        assert vertex_activations.shape == (N_VERTICES,), (
            f"Expected ({N_VERTICES},), got {vertex_activations.shape}"
        )

        # Combine hemisphere labels into single array
        all_labels = np.concatenate([self.labels_lh, self.labels_rh])

        regions: dict[str, RegionActivation] = {}

        for label_idx, label_name in enumerate(self.label_names):
            if label_name in EXCLUDED_LABELS:
                continue

            # Find vertices with this label in each hemisphere
            lh_mask = self.labels_lh == label_idx
            rh_mask = self.labels_rh == label_idx

            lh_indices = np.where(lh_mask)[0]
            rh_indices = np.where(rh_mask)[0] + N_LEFT  # offset for right hemisphere

            if bilateral_collapse:
                all_indices = np.concatenate([lh_indices, rh_indices])
                if len(all_indices) == 0:
                    continue
                activation = float(np.mean(vertex_activations[all_indices]))
                regions[label_name] = RegionActivation(
                    name=label_name,
                    hemisphere="bilateral",
                    activation=activation,
                    vertex_indices=all_indices,
                )
            else:
                if len(lh_indices) > 0:
                    key = f"L_{label_name}"
                    regions[key] = RegionActivation(
                        name=label_name,
                        hemisphere="L",
                        activation=float(np.mean(vertex_activations[lh_indices])),
                        vertex_indices=lh_indices,
                    )
                if len(rh_indices) > 0:
                    key = f"R_{label_name}"
                    regions[key] = RegionActivation(
                        name=label_name,
                        hemisphere="R",
                        activation=float(np.mean(vertex_activations[rh_indices])),
                        vertex_indices=rh_indices,
                    )

        logger.info("Mapped %d regions (bilateral_collapse=%s)", len(regions), bilateral_collapse)
        return regions

    def get_label_names(self) -> list[str]:
        """Return non-excluded label names."""
        return [n for n in self.label_names if n not in EXCLUDED_LABELS]
