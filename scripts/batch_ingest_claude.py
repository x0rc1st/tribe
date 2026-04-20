"""Bulk-ingest learning modules through the Claude predictor via the
Anthropic Message Batches API (50 % cheaper than live, ≤24 h turnaround).

Typical workflow — 100 modules in one overnight run::

    python scripts/batch_ingest_claude.py \
        --input /path/to/modules \
        --server http://localhost:8000 \
        --output /path/to/claude_results.json

Three modes are supported:

1. **Full workflow** (default): submit → poll → fetch → ingest into the
   running server's cache → (optionally) save raw results to JSON.
2. **Submit-only** (``--submit-only``): submit the batch and print the
   `batch_id`; useful when you want to detach and resume later.
3. **Resume** (``--batch-id <id>``): poll an existing batch, fetch results
   when it ends, and ingest + save as usual.

Input formats:

* A directory of ``.md`` / ``.txt`` files — each file becomes one module, the
  ``custom_id`` is the filename stem.
* A JSON file of ``{custom_id: text}`` pairs.

The script writes the raw Claude outputs (not the full PredictResponse) to
``--output`` so the post-processing cost stays on the server side — if the
Destrieux atlas or cognitive map is updated later, a single re-ingest call
per module regenerates the downstream response without re-paying Claude.

Requires:
  * `anthropic` in the current Python env
  * ``ANTHROPIC_API_KEY`` (or ``HTB_BRAIN_ANTHROPIC_API_KEY``) in env
  * The brain server running at ``--server`` (only if ingesting to cache)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# Make the package importable when run directly from a checkout.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from htb_brain.core.claude_predictor import ClaudePredictor  # noqa: E402

logger = logging.getLogger("batch_ingest_claude")


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------

def _load_inputs(path: Path) -> dict[str, str]:
    """Read modules from a directory of text files or a JSON map."""
    if path.is_dir():
        items: dict[str, str] = {}
        for fp in sorted(path.iterdir()):
            if fp.suffix.lower() in (".md", ".txt") and fp.is_file():
                items[fp.stem] = fp.read_text(encoding="utf-8")
        if not items:
            raise SystemExit(f"No .md or .txt files found in {path}")
        return items

    if path.is_file() and path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise SystemExit(
                f"{path} must contain a JSON object of {{custom_id: text}} pairs."
            )
        return {str(k): str(v) for k, v in raw.items()}

    raise SystemExit(f"Input path must be a directory or .json file: {path}")


# ---------------------------------------------------------------------------
# Batch orchestration
# ---------------------------------------------------------------------------

def _submit(predictor: ClaudePredictor, items: dict[str, str]) -> str:
    pairs = list(items.items())
    batch_id = predictor.submit_batch(pairs)
    logger.info("Batch submitted: %s (%d modules)", batch_id, len(pairs))
    return batch_id


def _poll_until_done(predictor: ClaudePredictor, batch_id: str, poll_seconds: int) -> None:
    """Block until the batch reaches a terminal state."""
    terminal = {"ended", "canceled", "expired"}
    started = time.time()
    while True:
        status = predictor.poll_batch(batch_id)
        elapsed = int(time.time() - started)
        logger.info(
            "[%s] status=%s counts=%s (elapsed %ds)",
            batch_id,
            status["status"],
            status.get("request_counts"),
            elapsed,
        )
        if status["status"] in terminal:
            return
        time.sleep(poll_seconds)


def _ingest_to_server(
    server_url: str,
    items: dict[str, str],
    results: dict[str, dict[str, Any]],
) -> int:
    """POST each raw Claude result to /api/v1/predict/claude/ingest. Returns
    the number of modules successfully ingested."""
    try:
        import httpx
    except ImportError:
        raise SystemExit(
            "`httpx` is required to push to a running server. "
            "Install it or run with --no-ingest."
        )

    url = server_url.rstrip("/") + "/api/v1/predict/claude/ingest"
    success = 0
    with httpx.Client(timeout=60.0) as client:
        for cid, parsed in results.items():
            text = items.get(cid)
            if text is None:
                logger.warning("No text found for custom_id=%s; skipping ingest.", cid)
                continue
            payload = {
                "text": text,
                "cortical_region_zscores": parsed["cortical_region_zscores"],
                "subcortical_region_zscores": parsed["subcortical_region_zscores"],
                "reasoning": parsed.get("reasoning", ""),
                "content_type": "text module",
            }
            try:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                success += 1
            except Exception as exc:
                logger.error("Ingest failed for %s: %s", cid, exc)
    logger.info("Ingested %d/%d modules into %s", success, len(results), server_url)
    return success


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--input", type=Path, help="Directory of .md/.txt files or a JSON {id: text} map.")
    parser.add_argument("--batch-id", help="Resume an existing batch instead of submitting a new one.")
    parser.add_argument("--server", default=os.environ.get("HTB_BRAIN_SERVER", "http://localhost:8000"),
                        help="Brain server URL to push results to (default: env HTB_BRAIN_SERVER or http://localhost:8000).")
    parser.add_argument("--output", type=Path, help="Write raw Claude results to this JSON file.")
    parser.add_argument("--no-ingest", action="store_true", help="Skip pushing to the running server.")
    parser.add_argument("--submit-only", action="store_true",
                        help="Submit the batch and exit; resume later with --batch-id.")
    parser.add_argument("--poll-seconds", type=int, default=60,
                        help="Seconds between batch status polls (default: 60).")
    parser.add_argument("--model", default=None, help="Override the Claude model id.")
    parser.add_argument("--thinking-budget", type=int, default=None,
                        help="Override the extended-thinking token budget (0 to disable).")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    api_key = os.environ.get("HTB_BRAIN_ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise SystemExit(
            "Set HTB_BRAIN_ANTHROPIC_API_KEY or ANTHROPIC_API_KEY in your environment."
        )

    predictor_kwargs: dict[str, Any] = {"api_key": api_key}
    if args.model:
        predictor_kwargs["model"] = args.model
    if args.thinking_budget is not None:
        predictor_kwargs["thinking_budget"] = args.thinking_budget
    predictor = ClaudePredictor(**predictor_kwargs)

    # Load inputs if we're submitting or we need text for ingest / output.
    items: dict[str, str] = {}
    if args.input:
        items = _load_inputs(args.input)
        logger.info("Loaded %d modules from %s", len(items), args.input)

    # Submit (or resume) --------------------------------------------------
    if args.batch_id:
        batch_id = args.batch_id
        logger.info("Resuming existing batch %s", batch_id)
    else:
        if not items:
            raise SystemExit("Provide --input (or --batch-id to resume).")
        batch_id = _submit(predictor, items)

    if args.submit_only:
        print(f"batch_id={batch_id}")
        return

    # Poll until terminal --------------------------------------------------
    _poll_until_done(predictor, batch_id, args.poll_seconds)

    # Fetch -----------------------------------------------------------------
    logger.info("Fetching results for %s", batch_id)
    results = predictor.fetch_batch_results(batch_id)
    logger.info("Fetched %d successful results", len(results))

    # Save raw outputs (optional) ------------------------------------------
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
        logger.info("Wrote raw Claude outputs to %s", args.output)

    # Ingest into running server (optional) --------------------------------
    if not args.no_ingest and items:
        _ingest_to_server(args.server, items, results)


if __name__ == "__main__":
    main()
