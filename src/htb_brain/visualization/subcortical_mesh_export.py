"""Export subcortical structure meshes to GLB for rendering inside the glass brain.

Generates marching-cubes meshes from the Harvard-Oxford subcortical atlas,
assigns each structure to a capability group, and exports a GLB with the same
_GROUPINDEX vertex attribute used by the cortical mesh.

The subcortical GLB is designed to be loaded **alongside** the cortical GLB in
the brain viewer. Both share the same MNI-aligned coordinate space.

Usage::

    # Generate standalone subcortical mesh
    python -m htb_brain.visualization.subcortical_mesh_export [output_path]

    # Generate combined cortical + subcortical mesh
    python -m htb_brain.visualization.subcortical_mesh_export --combined [output_path]
"""

from __future__ import annotations

import json
import logging
import struct
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
from nilearn import datasets
from scipy.ndimage import gaussian_filter
from skimage import measure

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Subcortical structure → capability group mapping
# ---------------------------------------------------------------------------

STRUCTURE_TO_GROUPS: dict[str, list[int]] = {
    "Thalamus":    [3, 5],  # Language relay + Attentional gating
    "Caudate":     [1],     # Goal-directed behavior → Strategic Thinking
    "Putamen":     [2],     # Procedural/habit learning → Procedural Fluency
    "Pallidum":    [2],     # Motor output gating → Procedural Fluency
    "Hippocampus": [7],     # Episodic memory → Memory Encoding
    "Amygdala":    [9],     # Threat detection → Rapid Assessment
    "Accumbens":   [6],     # Reward/motivation → Adaptive Response
}

# Harvard-Oxford labels to exclude (not brain parenchyma)
_MASK_EXCLUDED = ["Cortex", "White", "Stem", "Background"]
_CSF_LABELS = {
    "Left Lateral Ventricle", "Right Lateral Ventricle",
    "3rd Ventricle", "4th Ventricle",
}


# ---------------------------------------------------------------------------
# Atlas / mask helpers
# ---------------------------------------------------------------------------

def _get_subcortical_mask():
    """Load Harvard-Oxford subcortical atlas and build the inclusion mask."""
    atlas = datasets.fetch_atlas_harvard_oxford("sub-maxprob-thr50-2mm")
    excluded_indices = [
        i for i, label in enumerate(atlas.labels)
        if any(exc.lower() in label.lower() for exc in _MASK_EXCLUDED)
    ]
    mask_data = atlas.maps.get_fdata().copy()
    mask_data[np.isin(mask_data, excluded_indices)] = 0
    return mask_data, atlas


def _get_structure_mask(atlas, label: str) -> np.ndarray:
    """Get a binary mask for a named structure (merges Left+Right)."""
    labels = atlas.labels
    data = atlas.maps.get_fdata()

    if f"Left {label}" in labels:
        left_idx = labels.index(f"Left {label}")
        right_idx = labels.index(f"Right {label}")
        return ((data == left_idx) | (data == right_idx)).astype(float)
    elif label in labels:
        idx = labels.index(label)
        return (data == idx).astype(float)
    else:
        raise ValueError(f"Structure '{label}' not found in atlas")


def _mask_to_mesh(mask: np.ndarray, affine: np.ndarray, sigma: float = 1.0):
    """Convert a binary mask to a triangle mesh via marching cubes.

    Returns (vertices, faces) where vertices are in MNI world coordinates.
    """
    # Smooth mask slightly for nicer mesh
    volume = gaussian_filter(mask, sigma=sigma)

    # Marching cubes
    verts, faces, normals, values = measure.marching_cubes(volume, level=0.5)

    # Convert voxel coordinates to MNI world coordinates
    verts_world = nib.affines.apply_affine(affine, verts).astype(np.float32)
    faces = faces.astype(np.int32)

    return verts_world, faces


# ---------------------------------------------------------------------------
# Voxel-to-mesh mapping (for runtime activation transfer)
# ---------------------------------------------------------------------------

def build_voxel_to_vertex_map(
    structure_name: str,
    mesh_vertices: np.ndarray,
    atlas,
    mask_data: np.ndarray,
) -> np.ndarray:
    """Build a mapping from model output voxel indices to mesh vertex indices.

    For each mesh vertex, finds the nearest non-zero voxel in the subcortical
    mask and returns its index in the flattened non-zero array (which matches
    the model output ordering).

    Returns:
        voxel_indices: (n_mesh_vertices,) array of model output indices
    """
    affine = atlas.maps.affine
    inv_affine = np.linalg.inv(affine)

    # Get the flattened non-zero voxel coordinates
    nonzero_mask = mask_data > 0
    nonzero_coords = np.argwhere(nonzero_mask)  # (N_voxels, 3) in voxel space

    # Convert mesh vertices from MNI to voxel space
    mesh_voxel = nib.affines.apply_affine(inv_affine, mesh_vertices)

    # For each mesh vertex, find nearest non-zero voxel
    from scipy.spatial import cKDTree
    tree = cKDTree(nonzero_coords)
    _, indices = tree.query(mesh_voxel)

    return indices.astype(np.int32)


# ---------------------------------------------------------------------------
# GLB packing (reuses format from mesh_export.py)
# ---------------------------------------------------------------------------

def _pad4(data: bytes) -> bytes:
    remainder = len(data) % 4
    return data if remainder == 0 else data + b"\x00" * (4 - remainder)


def _pack_glb(vertices, faces, group_index) -> bytes:
    """Pack vertices, faces, and group indices into a binary GLB."""
    vertices = np.ascontiguousarray(vertices, dtype=np.float32)
    faces = np.ascontiguousarray(faces, dtype=np.uint32)
    group_index = np.ascontiguousarray(group_index, dtype=np.uint8)

    n_verts = len(vertices)

    indices_bytes = faces.tobytes()
    positions_bytes = vertices.tobytes()
    group_bytes = group_index.tobytes()

    indices_padded = _pad4(indices_bytes)
    positions_padded = _pad4(positions_bytes)
    group_padded = _pad4(group_bytes)

    bin_data = indices_padded + positions_padded + group_padded

    idx_offset = 0
    idx_len = len(indices_bytes)
    pos_offset = len(indices_padded)
    pos_len = len(positions_bytes)
    grp_offset = pos_offset + len(positions_padded)
    grp_len = len(group_bytes)

    v_min = vertices.min(axis=0).tolist()
    v_max = vertices.max(axis=0).tolist()

    gltf = {
        "asset": {"version": "2.0", "generator": "htb_brain.subcortical_mesh_export"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "subcortical"}],
        "meshes": [{
            "primitives": [{
                "attributes": {"POSITION": 1, "_GROUPINDEX": 2},
                "indices": 0,
                "mode": 4,
            }]
        }],
        "accessors": [
            {"bufferView": 0, "componentType": 5125, "count": faces.size,
             "type": "SCALAR", "max": [int(faces.max())], "min": [int(faces.min())]},
            {"bufferView": 1, "componentType": 5126, "count": n_verts,
             "type": "VEC3", "max": v_max, "min": v_min},
            {"bufferView": 2, "componentType": 5121, "count": n_verts,
             "type": "SCALAR", "max": [int(group_index.max())], "min": [int(group_index.min())]},
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": idx_offset, "byteLength": idx_len, "target": 34963},
            {"buffer": 0, "byteOffset": pos_offset, "byteLength": pos_len, "target": 34962},
            {"buffer": 0, "byteOffset": grp_offset, "byteLength": grp_len, "target": 34962},
        ],
        "buffers": [{"byteLength": len(bin_data)}],
    }

    json_str = json.dumps(gltf, separators=(",", ":"))
    while len(json_str) % 4 != 0:
        json_str += " "
    json_bytes = json_str.encode("utf-8")

    total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_data)
    buf = bytearray()
    buf += struct.pack("<I", 0x46546C67)
    buf += struct.pack("<I", 2)
    buf += struct.pack("<I", total_length)
    buf += struct.pack("<I", len(json_bytes))
    buf += struct.pack("<I", 0x4E4F534A)
    buf += json_bytes
    buf += struct.pack("<I", len(bin_data))
    buf += struct.pack("<I", 0x004E4942)
    buf += bin_data
    return bytes(buf)


# ---------------------------------------------------------------------------
# Main export pipeline
# ---------------------------------------------------------------------------

def export_subcortical_mesh(output_path: str | Path) -> dict:
    """Generate subcortical structure meshes and export as GLB.

    Returns a metadata dict with vertex counts and voxel-to-vertex mappings
    needed for runtime activation transfer.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Loading Harvard-Oxford subcortical atlas...")
    mask_data, atlas = _get_subcortical_mask()
    affine = atlas.maps.affine

    all_vertices = []
    all_faces = []
    all_groups = []
    structure_meta = {}
    vertex_offset = 0

    for structure_name, group_ids in STRUCTURE_TO_GROUPS.items():
        logger.info("Generating mesh for: %s (group %s)", structure_name, group_ids)

        try:
            mask = _get_structure_mask(atlas, structure_name)
        except ValueError as e:
            logger.warning("Skipping %s: %s", structure_name, e)
            continue

        if mask.sum() < 10:
            logger.warning("Skipping %s: too few voxels (%d)", structure_name, int(mask.sum()))
            continue

        verts, faces = _mask_to_mesh(mask, affine)

        # Use first group ID for coloring
        primary_group = group_ids[0]
        groups = np.full(len(verts), primary_group, dtype=np.uint8)

        # Build voxel-to-vertex map for this structure
        voxel_map = build_voxel_to_vertex_map(structure_name, verts, atlas, mask_data)

        structure_meta[structure_name] = {
            "vertex_start": vertex_offset,
            "vertex_count": len(verts),
            "face_count": len(faces),
            "group_ids": group_ids,
            "voxel_to_vertex_map": voxel_map,
        }

        # Offset faces for combined mesh
        faces_offset = faces + vertex_offset
        all_vertices.append(verts)
        all_faces.append(faces_offset)
        all_groups.append(groups)

        vertex_offset += len(verts)

        logger.info("  %s: %d vertices, %d faces", structure_name, len(verts), len(faces))

    if not all_vertices:
        raise RuntimeError("No subcortical structures could be meshed")

    # Combine all structures
    combined_verts = np.concatenate(all_vertices, axis=0)
    combined_faces = np.concatenate(all_faces, axis=0)
    combined_groups = np.concatenate(all_groups, axis=0)

    logger.info(
        "Combined subcortical mesh: %d vertices, %d faces, %d structures",
        len(combined_verts), len(combined_faces), len(structure_meta),
    )

    # Export GLB
    glb_bytes = _pack_glb(combined_verts, combined_faces, combined_groups)
    output_path.write_bytes(glb_bytes)
    logger.info("Wrote %.1f KB -> %s", len(glb_bytes) / 1024, output_path)

    # Save metadata (vertex maps needed at runtime for activation transfer)
    meta_path = output_path.with_suffix(".json")
    serializable_meta = {}
    for name, info in structure_meta.items():
        serializable_meta[name] = {
            "vertex_start": info["vertex_start"],
            "vertex_count": info["vertex_count"],
            "face_count": info["face_count"],
            "group_ids": info["group_ids"],
            "voxel_to_vertex_map": info["voxel_to_vertex_map"].tolist(),
        }
    meta_path.write_text(json.dumps(serializable_meta, indent=2))
    logger.info("Wrote metadata -> %s", meta_path)

    return structure_meta


def map_voxel_activations_to_mesh(
    voxel_activations: np.ndarray,
    meta_path: str | Path,
) -> np.ndarray:
    """Map subcortical model output (voxel activations) to mesh vertex activations.

    This is the runtime function called by the API to convert model output
    into values suitable for the 3D viewer.

    Args:
        voxel_activations: (n_subcortical_voxels,) from the subcortical model
        meta_path: path to the .json metadata saved by export_subcortical_mesh

    Returns:
        vertex_activations: (n_mesh_vertices,) activation per subcortical mesh vertex
    """
    with open(meta_path) as f:
        meta = json.load(f)

    total_vertices = sum(info["vertex_count"] for info in meta.values())
    vertex_acts = np.zeros(total_vertices, dtype=np.float32)

    for structure_name, info in meta.items():
        start = info["vertex_start"]
        count = info["vertex_count"]
        voxel_map = np.array(info["voxel_to_vertex_map"])

        # Clamp indices to valid range
        voxel_map = np.clip(voxel_map, 0, len(voxel_activations) - 1)

        # Transfer voxel activations to mesh vertices
        vertex_acts[start:start + count] = voxel_activations[voxel_map]

    return vertex_acts


# ---------------------------------------------------------------------------
# Combined cortical + subcortical export
# ---------------------------------------------------------------------------

def export_combined_mesh(output_path: str | Path) -> Path:
    """Export a single GLB containing both cortical surface and subcortical structures.

    Vertex layout:
        [0, 20483]        → cortical fsaverage5 (left + right hemisphere)
        [20484, 20484+N]  → subcortical structures

    The _GROUPINDEX attribute is set for all vertices (0-10).
    """
    from htb_brain.visualization.mesh_export import (
        _load_atlas_labels,
        _load_hemisphere,
        _build_group_index,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("=== Combined cortical + subcortical mesh export ===")

    # --- Cortical ---
    fsaverage = datasets.fetch_surf_fsaverage(mesh="fsaverage5")
    from nilearn.surface import load_surf_mesh

    verts_l, faces_l = _load_hemisphere(fsaverage, "left")
    verts_r, faces_r = _load_hemisphere(fsaverage, "right")
    labels_lh, labels_rh, label_names = _load_atlas_labels()
    groups_l = _build_group_index(labels_lh, label_names)
    groups_r = _build_group_index(labels_rh, label_names)

    n_left = len(verts_l)
    faces_r_offset = faces_r + n_left

    cortical_verts = np.concatenate([verts_l, verts_r], axis=0)
    cortical_faces = np.concatenate([faces_l, faces_r_offset], axis=0)
    cortical_groups = np.concatenate([groups_l, groups_r], axis=0)
    n_cortical = len(cortical_verts)

    logger.info("Cortical: %d vertices, %d faces", n_cortical, len(cortical_faces))

    # --- Subcortical ---
    mask_data, atlas = _get_subcortical_mask()
    affine = atlas.maps.affine

    subcort_verts_list = []
    subcort_faces_list = []
    subcort_groups_list = []
    subcort_meta = {}
    subcort_offset = n_cortical

    for structure_name, group_ids in STRUCTURE_TO_GROUPS.items():
        try:
            mask = _get_structure_mask(atlas, structure_name)
        except ValueError:
            continue
        if mask.sum() < 10:
            continue

        verts, faces = _mask_to_mesh(mask, affine)
        primary_group = group_ids[0]
        groups = np.full(len(verts), primary_group, dtype=np.uint8)

        voxel_map = build_voxel_to_vertex_map(structure_name, verts, atlas, mask_data)

        subcort_meta[structure_name] = {
            "vertex_start": subcort_offset,
            "vertex_count": len(verts),
            "group_ids": group_ids,
            "voxel_to_vertex_map": voxel_map.tolist(),
        }

        faces_offset = faces + subcort_offset
        subcort_verts_list.append(verts)
        subcort_faces_list.append(faces_offset)
        subcort_groups_list.append(groups)
        subcort_offset += len(verts)

        logger.info("  %s: %d vertices (group %d)", structure_name, len(verts), primary_group)

    # --- Combine ---
    all_verts = np.concatenate([cortical_verts] + subcort_verts_list, axis=0)
    all_faces = np.concatenate([cortical_faces] + subcort_faces_list, axis=0)
    all_groups = np.concatenate([cortical_groups] + subcort_groups_list, axis=0)

    n_subcortical = len(all_verts) - n_cortical
    logger.info(
        "Combined: %d total vertices (%d cortical + %d subcortical), %d faces",
        len(all_verts), n_cortical, n_subcortical, len(all_faces),
    )

    # Export GLB
    glb_bytes = _pack_glb(all_verts, all_faces, all_groups)
    output_path.write_bytes(glb_bytes)
    logger.info("Wrote %.1f KB -> %s", len(glb_bytes) / 1024, output_path)

    # Save metadata
    combined_meta = {
        "n_cortical_vertices": n_cortical,
        "n_subcortical_vertices": n_subcortical,
        "n_total_vertices": len(all_verts),
        "structures": {
            name: info for name, info in subcort_meta.items()
        },
    }
    meta_path = output_path.with_suffix(".json")
    meta_path.write_text(json.dumps(combined_meta, indent=2))
    logger.info("Wrote metadata -> %s", meta_path)

    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s  %(message)s")

    combined = "--combined" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--combined"]

    default_name = "brain_mesh_combined.glb" if combined else "subcortical_mesh.glb"
    default_out = f"/workspace/tribe/src/htb_brain/static/{default_name}"
    output = args[0] if args else default_out

    if combined:
        export_combined_mesh(output)
    else:
        export_subcortical_mesh(output)

    print(f"Done. Output: {output}")


if __name__ == "__main__":
    main()
