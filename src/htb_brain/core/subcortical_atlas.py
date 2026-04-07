"""Harvard-Oxford subcortical atlas — maps voxel predictions to named structures."""

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# Regions to exclude from the mask (same as tribev2/plotting/subcortical.py)
_MASK_EXCLUDED = ["Cortex", "White", "Stem", "Background"]

# CSF regions that survive the mask but aren't brain tissue — exclude from analysis
_CSF_LABELS = {
    "Left Lateral Ventricle",
    "Right Lateral Ventricle",
    "3rd Ventricle",
    "4th Ventricle",
}


@dataclass
class SubcorticalRegion:
    """A single subcortical structure with its predicted activation."""
    name: str          # e.g. "Thalamus"
    hemisphere: str    # "L", "R", or "bilateral"
    activation: float
    voxel_indices: np.ndarray  # indices into the model output vector


class SubcorticalAtlas:
    """Maps subcortical model output voxels to named Harvard-Oxford structures.

    The voxel order matches the MaskProjector(mask="subcortical") used during
    training: non-zero voxels from the Harvard-Oxford subcortical atlas at 2mm,
    after excluding Cortex/White/Stem/Background, in ravel (C-order) order.
    """

    def __init__(self):
        self.n_voxels: int = 0
        self.voxel_labels: np.ndarray | None = None  # label index per output voxel
        self.label_names: list[str] = []
        self._loaded = False

    def load(self):
        """Load the Harvard-Oxford subcortical atlas and build the voxel mapping."""
        from nilearn import datasets
        import nibabel as nib

        atlas = datasets.fetch_atlas_harvard_oxford("sub-maxprob-thr50-2mm")
        self.label_names = list(atlas.labels)

        # Build the same mask used by MaskProjector during training
        excluded_indices = [
            i for i, label in enumerate(self.label_names)
            if any(exc.lower() in label.lower() for exc in _MASK_EXCLUDED)
        ]
        mask_data = atlas.maps.get_fdata().copy()
        mask_data[np.isin(mask_data, excluded_indices)] = 0

        # The model output vector corresponds to non-zero voxels in ravel order
        nonzero_mask = mask_data > 0
        self.voxel_labels = mask_data[nonzero_mask].astype(int)
        self.n_voxels = len(self.voxel_labels)

        logger.info(
            "SubcorticalAtlas loaded: %d voxels, %d labels, %d excluded",
            self.n_voxels, len(self.label_names), len(excluded_indices),
        )
        self._loaded = True

    def map_activations(
        self, voxel_activations: np.ndarray, bilateral_collapse: bool = True
    ) -> dict[str, SubcorticalRegion]:
        """Map per-voxel activations to named subcortical structures.

        Args:
            voxel_activations: (n_voxels,) mean activation per voxel
            bilateral_collapse: if True, merge Left+Right into a single region

        Returns:
            dict of region_name -> SubcorticalRegion
        """
        assert self._loaded, "Atlas not loaded. Call load() first."
        assert voxel_activations.shape == (self.n_voxels,), (
            f"Expected ({self.n_voxels},), got {voxel_activations.shape}"
        )

        regions: dict[str, SubcorticalRegion] = {}

        for label_idx, label_name in enumerate(self.label_names):
            # Skip excluded labels and CSF
            if label_name in _CSF_LABELS:
                continue
            if any(exc.lower() in label_name.lower() for exc in _MASK_EXCLUDED):
                continue
            if label_idx == 0:  # Background
                continue

            voxel_mask = self.voxel_labels == label_idx
            indices = np.where(voxel_mask)[0]

            if len(indices) == 0:
                continue

            activation = float(np.mean(voxel_activations[indices]))

            if bilateral_collapse:
                # Strip "Left "/"Right " prefix and merge
                clean_name = label_name
                for prefix in ["Left ", "Right "]:
                    if label_name.startswith(prefix):
                        clean_name = label_name[len(prefix):]
                        break

                if clean_name in regions:
                    # Merge with existing (other hemisphere)
                    existing = regions[clean_name]
                    all_indices = np.concatenate([existing.voxel_indices, indices])
                    merged_activation = float(np.mean(voxel_activations[all_indices]))
                    regions[clean_name] = SubcorticalRegion(
                        name=clean_name,
                        hemisphere="bilateral",
                        activation=merged_activation,
                        voxel_indices=all_indices,
                    )
                else:
                    hemi = "L" if label_name.startswith("Left") else (
                        "R" if label_name.startswith("Right") else "bilateral"
                    )
                    regions[clean_name] = SubcorticalRegion(
                        name=clean_name,
                        hemisphere=hemi,
                        activation=activation,
                        voxel_indices=indices,
                    )
            else:
                hemi = "L" if label_name.startswith("Left") else (
                    "R" if label_name.startswith("Right") else "bilateral"
                )
                regions[label_name] = SubcorticalRegion(
                    name=label_name,
                    hemisphere=hemi,
                    activation=activation,
                    voxel_indices=indices,
                )

        logger.info("Mapped %d subcortical regions (bilateral_collapse=%s)",
                     len(regions), bilateral_collapse)
        return regions

    def get_region_names(self, bilateral: bool = True) -> list[str]:
        """Return available subcortical structure names."""
        names = set()
        for label in self.label_names:
            if label in _CSF_LABELS:
                continue
            if any(exc.lower() in label.lower() for exc in _MASK_EXCLUDED):
                continue
            if label == "Background":
                continue
            if bilateral:
                for prefix in ["Left ", "Right "]:
                    if label.startswith(prefix):
                        label = label[len(prefix):]
                        break
            names.add(label)
        return sorted(names)
