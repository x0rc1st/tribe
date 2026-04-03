"""Phase 2 validation — translation layer + summary generation."""

import json
import logging
import sys
import time

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("validate_p2")

sys.path.insert(0, "/workspace/tribe/src")

SAMPLE = """SQL injection is a code injection technique used to attack data-driven applications.
Malicious SQL statements are inserted into entry fields for execution by the backend database.
The attacker can bypass authentication, access sensitive data, modify database contents,
and execute admin operations. Prevention includes parameterized queries, stored procedures,
input validation, and least privilege."""


def main():
    log.info("STEP 1: Run prediction pipeline...")
    from htb_brain.core.atlas import BrainAtlas
    from htb_brain.core.predictor import BrainPredictor
    from htb_brain.core.aggregator import Aggregator

    atlas = BrainAtlas()
    atlas.load()

    predictor = BrainPredictor(
        model_repo="facebook/tribev2",
        cache_dir="/workspace/tribe/cache",
        device="auto",
    )
    predictor.load()

    preds, _ = predictor.predict_text(SAMPLE)
    agg = Aggregator(atlas=atlas)
    result = agg.process_prediction(preds)

    log.info("STEP 2: Translate to capability groups...")
    from htb_brain.core.translator import Translator

    translator = Translator("/workspace/tribe/src/htb_brain/data/cognitive_map.json")
    translator.load()

    group_scores = translator.translate(result["regions"], result["region_zscores"])

    log.info("\n=== CAPABILITY GROUP RANKINGS ===")
    for gs in group_scores:
        marker = " <<<" if gs.rank <= 3 else ""
        log.info("  #%d  %-45s z=%.3f%s", gs.rank, gs.name, gs.score, marker)

    log.info("\nSTEP 3: Generate narrative summary...")
    from htb_brain.visualization.summary import generate_summary

    summary = generate_summary(group_scores, content_type="text module")
    log.info("\n" + summary)

    log.info("\n=== PHASE 2 COMPLETE ===")
    log.info("Groups: %d", len(group_scores))
    log.info("Top group: %s (z=%.3f)", group_scores[0].name, group_scores[0].score)

    # Verify Technical Comprehension ranks in top 3 for text input
    top3_names = [gs.name for gs in group_scores[:3]]
    assert "Technical Comprehension & Language Processing" in top3_names, (
        f"Expected 'Technical Comprehension' in top 3, got {top3_names}"
    )
    log.info("ASSERTION PASSED: Technical Comprehension in top 3")


if __name__ == "__main__":
    main()
