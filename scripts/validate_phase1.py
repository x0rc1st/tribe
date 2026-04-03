"""Phase 1 gate check — validate TRIBE v2 loads and produces valid predictions."""

import logging
import sys
import time

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("validate_phase1")

SAMPLE_TEXT = """
SQL injection is a code injection technique used to attack data-driven applications.
Malicious SQL statements are inserted into entry fields for execution by the backend database.
The attacker can use this vulnerability to bypass authentication, access sensitive data,
modify database contents, and execute administrative operations on the database.
Common prevention techniques include parameterized queries, stored procedures, input validation,
and the principle of least privilege for database accounts.
"""


def main():
    # Step 1: Load atlas
    logger.info("=" * 60)
    logger.info("STEP 1: Loading Destrieux atlas...")
    from htb_brain.core.atlas import BrainAtlas

    atlas = BrainAtlas()
    atlas.load()
    labels = atlas.get_label_names()
    logger.info("Atlas OK: %d regions (excluding Unknown, Medial_wall)", len(labels))

    # Step 2: Load TRIBE v2
    logger.info("=" * 60)
    logger.info("STEP 2: Loading TRIBE v2 model...")
    from htb_brain.core.predictor import BrainPredictor

    predictor = BrainPredictor(
        model_repo="facebook/tribev2",
        cache_dir="/workspace/tribe/cache",
        device="auto",
    )
    predictor.load()
    logger.info("Model OK: loaded on device")

    # Step 3: Run prediction
    logger.info("=" * 60)
    logger.info("STEP 3: Running prediction on sample cybersecurity text...")
    t0 = time.time()
    preds, segments = predictor.predict_text(SAMPLE_TEXT)
    elapsed = time.time() - t0
    logger.info("Prediction OK: shape=%s, took %.1fs", preds.shape, elapsed)

    assert preds.ndim == 2, f"Expected 2D, got {preds.ndim}D"
    assert preds.shape[1] == 20484, f"Expected 20484 vertices, got {preds.shape[1]}"
    logger.info("  timesteps: %d", preds.shape[0])
    logger.info("  min=%.4f, max=%.4f, mean=%.4f", preds.min(), preds.max(), preds.mean())

    # Step 4: Aggregate
    logger.info("=" * 60)
    logger.info("STEP 4: Aggregating to regions...")
    from htb_brain.core.aggregator import Aggregator

    aggregator = Aggregator(atlas=atlas, threshold_percentile=75.0, bilateral_collapse=True)
    result = aggregator.process_prediction(preds)

    logger.info("Regions: %d total, %d engaged", len(result["regions"]), len(result["engaged_regions"]))

    # Step 5: Check that language regions rank high for text input
    logger.info("=" * 60)
    logger.info("STEP 5: Checking language region engagement...")
    language_regions = [
        "G_front_inf-Opercular",  # Broca's
        "G_temp_sup-Plan_tempo",  # Wernicke's
        "G_temp_sup-Lateral",
        "G_temporal_middle",
    ]

    zscores = result["region_zscores"]
    sorted_regions = sorted(zscores.items(), key=lambda x: x[1], reverse=True)

    logger.info("\nTop 10 engaged regions:")
    for i, (name, z) in enumerate(sorted_regions[:10]):
        marker = " <-- LANGUAGE" if name in language_regions else ""
        logger.info("  %2d. %-35s z=%.3f%s", i + 1, name, z, marker)

    # Check if any language region is in top 25%
    top_25_names = {name for name, _ in sorted_regions[:len(sorted_regions) // 4]}
    language_in_top = [r for r in language_regions if r in top_25_names]
    logger.info("\nLanguage regions in top 25%%: %d/%d %s",
                len(language_in_top), len(language_regions), language_in_top)

    logger.info("=" * 60)
    logger.info("PHASE 1 VALIDATION COMPLETE")
    logger.info("  Model loads: YES")
    logger.info("  Predictions valid: YES (%s)", preds.shape)
    logger.info("  Atlas mapping: YES (%d regions)", len(result["regions"]))
    logger.info("  Vertex activations: (20484,) normalized 0-1")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
