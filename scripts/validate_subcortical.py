#!/usr/bin/env python3
"""
Validate the subcortical prediction pipeline.

This script tests the subcortical components independently of the training
pipeline. It verifies:
  1. SubcorticalAtlas loads and maps correctly
  2. SubcorticalAggregator produces valid region/group scores
  3. SubcorticalPredictor loads and runs inference (if a checkpoint exists)

Usage:
    # Test atlas + aggregator only (no GPU or checkpoint needed)
    python scripts/validate_subcortical.py

    # Also test inference with a trained checkpoint
    python scripts/validate_subcortical.py --checkpoint-dir /path/to/subcortical/results
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def test_atlas():
    """Test SubcorticalAtlas loading and region mapping."""
    print("\n=== Testing SubcorticalAtlas ===")

    from htb_brain.core.subcortical_atlas import SubcorticalAtlas
    import numpy as np

    atlas = SubcorticalAtlas()
    atlas.load()

    print(f"  Voxels: {atlas.n_voxels}")
    print(f"  Labels: {len(atlas.label_names)}")

    region_names = atlas.get_region_names(bilateral=True)
    print(f"  Bilateral regions: {region_names}")

    # Simulate random activations
    fake_activations = np.random.randn(atlas.n_voxels).astype(np.float32)

    # Test bilateral mapping
    regions_bilateral = atlas.map_activations(fake_activations, bilateral_collapse=True)
    print(f"\n  Bilateral mapping ({len(regions_bilateral)} regions):")
    for name, region in sorted(regions_bilateral.items()):
        print(f"    {name}: activation={region.activation:.4f}, "
              f"voxels={len(region.voxel_indices)}, hemi={region.hemisphere}")

    # Test per-hemisphere mapping
    regions_split = atlas.map_activations(fake_activations, bilateral_collapse=False)
    print(f"\n  Per-hemisphere mapping ({len(regions_split)} regions):")
    for name, region in sorted(regions_split.items()):
        print(f"    {name}: activation={region.activation:.4f}, "
              f"voxels={len(region.voxel_indices)}, hemi={region.hemisphere}")

    # Verify all voxels are accounted for (excluding CSF)
    all_indices = set()
    for r in regions_bilateral.values():
        all_indices.update(r.voxel_indices.tolist())
    coverage = len(all_indices) / atlas.n_voxels * 100
    print(f"\n  Voxel coverage (excl. CSF): {len(all_indices)}/{atlas.n_voxels} ({coverage:.1f}%)")

    assert len(regions_bilateral) > 0, "No regions mapped!"
    assert "Thalamus" in regions_bilateral, "Thalamus not found!"
    assert "Hippocampus" in regions_bilateral, "Hippocampus not found!"
    assert "Amygdala" in regions_bilateral, "Amygdala not found!"

    print("\n  PASS: SubcorticalAtlas works correctly")
    return atlas


def test_aggregator(atlas):
    """Test SubcorticalAggregator with synthetic data."""
    print("\n=== Testing SubcorticalAggregator ===")

    from htb_brain.core.subcortical_aggregator import SubcorticalAggregator
    import numpy as np

    agg = SubcorticalAggregator(atlas)

    # Simulate model output: (10 timesteps, n_voxels)
    fake_preds = np.random.randn(10, atlas.n_voxels).astype(np.float32)

    result = agg.process_prediction(fake_preds)

    print(f"  Regions: {len(result['regions'])}")
    print(f"  Engaged: {result['engaged_regions']}")
    print(f"  Threshold: {result['threshold_value']:.3f}")
    print(f"  Group scores:")
    for gid, score in sorted(result["group_scores"].items()):
        print(f"    Group {gid}: {score:.4f}")

    assert "regions" in result
    assert "region_zscores" in result
    assert "engaged_regions" in result
    assert "group_scores" in result
    assert len(result["group_scores"]) > 0

    print("\n  PASS: SubcorticalAggregator works correctly")


def test_predictor(checkpoint_dir: str):
    """Test SubcorticalPredictor with a real checkpoint."""
    print(f"\n=== Testing SubcorticalPredictor (checkpoint: {checkpoint_dir}) ===")

    from htb_brain.core.subcortical_predictor import SubcorticalPredictor
    from htb_brain.core.subcortical_atlas import SubcorticalAtlas
    from htb_brain.core.subcortical_aggregator import SubcorticalAggregator

    predictor = SubcorticalPredictor(
        checkpoint_dir=checkpoint_dir,
        cache_dir="./cache",
        device="auto",
    )
    predictor.load()
    print(f"  Model loaded: {predictor.n_outputs} output voxels")

    # Test with sample text
    test_text = (
        "SQL injection is a code injection technique that exploits a security "
        "vulnerability in an application's software. The attacker sends malicious "
        "SQL statements through the application to the backend database."
    )

    print("  Running prediction on sample text...")
    preds, segments = predictor.predict_text(test_text)
    print(f"  Prediction shape: {preds.shape}")
    print(f"  Segments: {len(segments)}")

    # Run through aggregator
    atlas = SubcorticalAtlas()
    atlas.load()
    assert preds.shape[1] == atlas.n_voxels, (
        f"Model outputs {preds.shape[1]} voxels but atlas expects {atlas.n_voxels}"
    )

    agg = SubcorticalAggregator(atlas)
    result = agg.process_prediction(preds)

    print(f"\n  Subcortical region scores:")
    for name, z in sorted(result["region_zscores"].items(), key=lambda x: -x[1]):
        marker = " <<" if name in result["engaged_regions"] else ""
        print(f"    {name}: z={z:.3f}{marker}")

    print(f"\n  Group contributions:")
    for gid, score in sorted(result["group_scores"].items(), key=lambda x: -x[1]):
        print(f"    Group {gid}: {score:.3f}")

    print("\n  PASS: SubcorticalPredictor works correctly")


def main():
    parser = argparse.ArgumentParser(description="Validate subcortical pipeline")
    parser.add_argument(
        "--checkpoint-dir", type=str, default=None,
        help="Path to trained subcortical model (optional — skips inference test if not provided)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Subcortical Pipeline Validation")
    print("=" * 60)

    # Always test atlas + aggregator
    atlas = test_atlas()
    test_aggregator(atlas)

    # Optionally test full inference
    if args.checkpoint_dir:
        test_predictor(args.checkpoint_dir)
    else:
        print("\n  Skipping predictor test (no --checkpoint-dir provided)")

    print("\n" + "=" * 60)
    print("  All tests PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
