"""Export fsaverage5 brain mesh to GLB with per-vertex capability-group indices.

Loads the Destrieux atlas on the fsaverage5 surface, assigns each vertex to one
of the 10 TRIBE capability groups (or 0 for unassigned / medial wall), combines
left + right hemispheres into a single mesh, and writes a binary GLB file with
a custom ``_GROUPINDEX`` vertex attribute baked in.

Usage::

    python mesh_export.py [output_path]

If *output_path* is omitted it defaults to
``/workspace/tribe/src/htb_brain/static/brain_mesh.glb``.
"""

from __future__ import annotations

import json
import logging
import struct
import sys
from pathlib import Path

import numpy as np
from nilearn import datasets
from nilearn.surface import load_surf_mesh

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (matching atlas.py)
# ---------------------------------------------------------------------------

N_VERTICES = 20484
N_LEFT = 10242

# ---------------------------------------------------------------------------
# Region -> capability-group mapping (Destrieux atlas labels)
# ---------------------------------------------------------------------------

# Mapping from Destrieux atlas label name to capability-group id (1-10).
# Labels not present here (e.g. "Unknown", "Medial_wall") map to 0.

REGION_TO_GROUP: dict[str, int] = {}

_GROUP_REGIONS: dict[int, list[str]] = {
    1: [
        "G_front_sup", "G_front_middle", "G_front_inf-Triangul",
        "G_front_inf-Orbital", "G_orbital", "G_rectus",
        "G_and_S_frontomargin", "G_and_S_transv_frontopol",
        "S_front_sup", "S_front_middle", "S_front_inf",
        "S_orbital_lateral", "S_orbital_med-olfact",
        "S_orbital-H_Shaped", "S_suborbital",
    ],
    2: [
        "G_precentral", "G_postcentral", "G_and_S_paracentral",
        "G_and_S_subcentral", "S_central", "S_precentral-inf-part",
        "S_precentral-sup-part", "S_postcentral",
    ],
    3: [
        "G_front_inf-Opercular", "G_temp_sup-Lateral",
        "G_temp_sup-Plan_tempo", "G_temp_sup-Plan_polar",
        "G_temp_sup-G_T_transv", "G_temporal_middle",
        "S_temporal_sup", "S_temporal_transverse",
        "Lat_Fis-ant-Horizont", "Lat_Fis-ant-Vertical",
        "Lat_Fis-post",
    ],
    4: [
        "G_cuneus", "G_occipital_sup", "G_occipital_middle",
        "G_and_S_occipital_inf", "Pole_occipital",
        "G_oc-temp_lat-fusifor", "G_oc-temp_med-Lingual",
        "G_temporal_inf", "S_calcarine", "S_occipital_ant",
        "S_oc_middle_and_Lunatus", "S_oc_sup_and_transversal",
        "S_oc-temp_lat", "S_oc-temp_med_and_Lingual",
        "S_temporal_inf", "S_parieto_occipital",
    ],
    5: [
        "G_parietal_sup", "S_intrapariet_and_P_trans", "S_subparietal",
    ],
    6: [
        "G_and_S_cingul-Ant", "G_and_S_cingul-Mid-Ant",
        "G_and_S_cingul-Mid-Post", "S_cingul-Marginalis",
        "S_pericallosal",
    ],
    7: [
        "G_oc-temp_med-Parahip", "Pole_temporal",
        "S_collat_transv_ant", "S_collat_transv_post",
    ],
    8: [
        "G_pariet_inf-Angular", "G_pariet_inf-Supramar",
        "S_interm_prim-Jensen",
    ],
    9: [
        "G_insular_short", "G_Ins_lg_and_S_cent_ins",
        "S_circular_insula_ant", "S_circular_insula_inf",
        "S_circular_insula_sup",
    ],
    10: [
        "G_cingul-Post-dorsal", "G_cingul-Post-ventral",
        "G_precuneus", "G_subcallosal",
    ],
}

for _gid, _regions in _GROUP_REGIONS.items():
    for _r in _regions:
        REGION_TO_GROUP[_r] = _gid


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _load_atlas_labels() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return Destrieux atlas parcellation arrays and label names.

    Uses the same ``fetch_atlas_surf_destrieux`` call as
    :class:`htb_brain.core.atlas.BrainAtlas`.

    Returns
    -------
    labels_lh : ndarray of int, shape (10242,)
    labels_rh : ndarray of int, shape (10242,)
    label_names : list[str]  (index -> label name, e.g. "G_front_sup")
    """
    destrieux = datasets.fetch_atlas_surf_destrieux()

    labels_lh = np.asarray(destrieux["map_left"])
    labels_rh = np.asarray(destrieux["map_right"])
    label_names = [
        lbl.decode("utf-8") if isinstance(lbl, bytes) else str(lbl)
        for lbl in destrieux["labels"]
    ]

    total = len(labels_lh) + len(labels_rh)
    assert total == N_VERTICES, f"Expected {N_VERTICES} vertices, got {total}"
    logger.info(
        "Destrieux atlas: %d labels, %d vertices (L=%d R=%d)",
        len(label_names), total, len(labels_lh), len(labels_rh),
    )
    return labels_lh, labels_rh, label_names


def _build_group_index(labels: np.ndarray, label_names: list[str]) -> np.ndarray:
    """Map each vertex's atlas label to a capability-group index (0-10).

    Parameters
    ----------
    labels : ndarray of int, shape (n_vertices,)
        Per-vertex atlas label indices.
    label_names : list[str]
        Atlas label names indexed by label value.

    Returns
    -------
    groups : ndarray of uint8, shape (n_vertices,)
    """
    groups = np.zeros(len(labels), dtype=np.uint8)
    for idx, name in enumerate(label_names):
        gid = REGION_TO_GROUP.get(name, 0)
        mask = labels == idx
        groups[mask] = gid
    return groups


def _load_hemisphere(fsaverage: dict, hemi: str) -> tuple[np.ndarray, np.ndarray]:
    """Load vertices and faces for one hemisphere.

    Parameters
    ----------
    fsaverage : dict
        Result of ``datasets.fetch_surf_fsaverage(mesh="fsaverage5")``.
    hemi : {"left", "right"}

    Returns
    -------
    vertices : ndarray float32 (N, 3)
    faces : ndarray int32 (F, 3)
    """
    mesh = load_surf_mesh(fsaverage[f"pial_{hemi}"])
    coords = np.asarray(mesh[0], dtype=np.float32)
    faces = np.asarray(mesh[1], dtype=np.int32)
    return coords, faces


# ---------------------------------------------------------------------------
# GLB export
# ---------------------------------------------------------------------------

def _pack_glb(
    vertices: np.ndarray,
    faces: np.ndarray,
    group_index: np.ndarray,
) -> bytes:
    """Build a minimal binary GLB with a custom ``_GROUPINDEX`` vertex attribute.

    The output conforms to glTF 2.0.  The ``_GROUPINDEX`` attribute is stored
    as a ``SCALAR`` accessor with ``componentType`` 5121 (UNSIGNED_BYTE) and
    values in the range 0-10.

    Parameters
    ----------
    vertices : (N, 3) float32
    faces : (F, 3) uint32
    group_index : (N,) uint8 -- values 0-10

    Returns
    -------
    glb_bytes : bytes  (complete GLB file content)
    """
    vertices = np.ascontiguousarray(vertices, dtype=np.float32)
    faces = np.ascontiguousarray(faces, dtype=np.uint32)
    group_index = np.ascontiguousarray(group_index, dtype=np.uint8)

    n_verts = len(vertices)
    n_faces = len(faces)

    # --- Binary buffer ---
    # Layout: [indices | positions | group_index]
    # Each section is padded to 4-byte alignment as required by glTF.
    indices_bytes = faces.tobytes()
    positions_bytes = vertices.tobytes()
    group_bytes = group_index.tobytes()

    def _pad4(data: bytes) -> bytes:
        remainder = len(data) % 4
        if remainder == 0:
            return data
        return data + b"\x00" * (4 - remainder)

    indices_padded = _pad4(indices_bytes)
    positions_padded = _pad4(positions_bytes)
    group_padded = _pad4(group_bytes)

    bin_data = indices_padded + positions_padded + group_padded

    # Byte offsets and lengths for bufferViews
    idx_offset = 0
    idx_len = len(indices_bytes)

    pos_offset = len(indices_padded)
    pos_len = len(positions_bytes)

    grp_offset = pos_offset + len(positions_padded)
    grp_len = len(group_bytes)

    # Vertex position bounds (required by glTF spec for POSITION)
    v_min = vertices.min(axis=0).tolist()
    v_max = vertices.max(axis=0).tolist()

    # --- glTF JSON descriptor ---
    gltf = {
        "asset": {"version": "2.0", "generator": "htb_brain.mesh_export"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "brain"}],
        "meshes": [
            {
                "primitives": [
                    {
                        "attributes": {
                            "POSITION": 1,
                            "_GROUPINDEX": 2,
                        },
                        "indices": 0,
                        "mode": 4,  # TRIANGLES
                    }
                ]
            }
        ],
        "accessors": [
            {
                # accessor 0 -- triangle indices
                "bufferView": 0,
                "componentType": 5125,  # UNSIGNED_INT
                "count": n_faces * 3,
                "type": "SCALAR",
                "max": [int(faces.max())],
                "min": [int(faces.min())],
            },
            {
                # accessor 1 -- vertex positions
                "bufferView": 1,
                "componentType": 5126,  # FLOAT
                "count": n_verts,
                "type": "VEC3",
                "max": v_max,
                "min": v_min,
            },
            {
                # accessor 2 -- group index per vertex
                "bufferView": 2,
                "componentType": 5121,  # UNSIGNED_BYTE
                "count": n_verts,
                "type": "SCALAR",
                "max": [int(group_index.max())],
                "min": [int(group_index.min())],
            },
        ],
        "bufferViews": [
            {
                # bufferView 0 -- indices
                "buffer": 0,
                "byteOffset": idx_offset,
                "byteLength": idx_len,
                "target": 34963,  # ELEMENT_ARRAY_BUFFER
            },
            {
                # bufferView 1 -- positions
                "buffer": 0,
                "byteOffset": pos_offset,
                "byteLength": pos_len,
                "target": 34962,  # ARRAY_BUFFER
            },
            {
                # bufferView 2 -- group index
                "buffer": 0,
                "byteOffset": grp_offset,
                "byteLength": grp_len,
                "target": 34962,  # ARRAY_BUFFER
            },
        ],
        "buffers": [
            {"byteLength": len(bin_data)},
        ],
    }

    json_str = json.dumps(gltf, separators=(",", ":"))
    # Pad JSON chunk to 4-byte boundary (spec requires space padding for JSON)
    while len(json_str) % 4 != 0:
        json_str += " "
    json_bytes = json_str.encode("utf-8")

    # --- Assemble GLB container ---
    # GLB header (12 bytes) + JSON chunk (8 + data) + BIN chunk (8 + data)
    total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_data)

    buf = bytearray()
    # GLB header
    buf += struct.pack("<I", 0x46546C67)   # magic "glTF"
    buf += struct.pack("<I", 2)            # version
    buf += struct.pack("<I", total_length)
    # JSON chunk
    buf += struct.pack("<I", len(json_bytes))
    buf += struct.pack("<I", 0x4E4F534A)   # chunk type "JSON"
    buf += json_bytes
    # BIN chunk
    buf += struct.pack("<I", len(bin_data))
    buf += struct.pack("<I", 0x004E4942)   # chunk type "BIN\0"
    buf += bin_data

    return bytes(buf)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def export_brain_mesh(output_path: str | Path) -> Path:
    """Build and export the combined brain mesh as GLB.

    Steps:

    1. Load the fsaverage5 pial surface (left + right hemispheres).
    2. Load the Destrieux surface atlas parcellation.
    3. Map each vertex to a capability-group index (0-10).
    4. Combine both hemispheres into a single mesh (left first, then right).
    5. Write a binary GLB with ``POSITION`` and ``_GROUPINDEX`` attributes.

    Parameters
    ----------
    output_path : path-like
        Destination ``.glb`` file.

    Returns
    -------
    Path to the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Loading fsaverage5 surface and Destrieux atlas ...")
    fsaverage = datasets.fetch_surf_fsaverage(mesh="fsaverage5")

    # -- Surface geometry --
    verts_l, faces_l = _load_hemisphere(fsaverage, "left")
    verts_r, faces_r = _load_hemisphere(fsaverage, "right")

    logger.info(
        "Left hemisphere:  %d vertices, %d faces", len(verts_l), len(faces_l),
    )
    logger.info(
        "Right hemisphere: %d vertices, %d faces", len(verts_r), len(faces_r),
    )

    # -- Atlas parcellation --
    labels_lh, labels_rh, label_names = _load_atlas_labels()

    # -- Per-vertex group indices --
    groups_l = _build_group_index(labels_lh, label_names)
    groups_r = _build_group_index(labels_rh, label_names)

    for hemi_name, grp in [("LH", groups_l), ("RH", groups_r)]:
        assigned = int(np.count_nonzero(grp))
        logger.info(
            "%s: %d / %d vertices assigned to a capability group (%.1f%%)",
            hemi_name, assigned, len(grp), 100.0 * assigned / len(grp),
        )

    # -- Combine hemispheres --
    # Left vertices: indices 0 .. N_LEFT-1
    # Right vertices: indices N_LEFT .. N_VERTICES-1
    n_left = len(verts_l)
    faces_r_offset = faces_r + n_left

    vertices = np.concatenate([verts_l, verts_r], axis=0)
    faces = np.concatenate([faces_l, faces_r_offset], axis=0)
    group_index = np.concatenate([groups_l, groups_r], axis=0)

    logger.info(
        "Combined mesh: %d vertices (%d + %d), %d faces",
        len(vertices), n_left, len(verts_r), len(faces),
    )
    logger.info(
        "Vertex ranges -- Left: 0-%d  Right: %d-%d",
        n_left - 1, n_left, len(vertices) - 1,
    )

    # Log group distribution
    unique, counts = np.unique(group_index, return_counts=True)
    for g, c in zip(unique, counts):
        logger.info("  Group %2d: %5d vertices", g, c)

    # -- Export --
    glb_bytes = _pack_glb(vertices, faces, group_index)
    output_path.write_bytes(glb_bytes)

    size_kb = len(glb_bytes) / 1024
    logger.info("Wrote %.1f KB -> %s", size_kb, output_path)

    return output_path


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s  %(message)s",
    )

    default_out = "/workspace/tribe/src/htb_brain/static/brain_mesh.glb"
    output = sys.argv[1] if len(sys.argv) > 1 else default_out

    result = export_brain_mesh(output)
    print(f"Done. Output: {result}")


if __name__ == "__main__":
    main()
