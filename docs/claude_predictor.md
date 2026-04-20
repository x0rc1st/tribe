# Claude Predictor — Feature Notes

Third prediction mode alongside the TRIBE conservative and neuroscience
blends. Bypasses TRIBE entirely and has Claude (Opus 4.7 by default) predict
per-Destrieux-region + per-Harvard-Oxford-structure z-scores **from first
principles** — using the full breadth of the cognitive-neuroscience and
learning-science literature, not by emulating any specific trained model.
Claude is a **parallel predictor** to TRIBE, not an emulator — they are two
independent estimators feeding the same response shape. The same downstream
pipeline that TRIBE output goes through — Translator, conservative blend,
neuroscience blend, narrative, operator-readiness, completion classifier —
runs on Claude's z-scores, so the response shape and glass-brain render are
byte-identical to the TRIBE path.

## Activation

1. `pip install -e .` to pick up the `anthropic` dependency.
2. `export ANTHROPIC_API_KEY=<key>` (or the `HTB_BRAIN_ANTHROPIC_API_KEY`
   variant — both are recognised).
3. Restart the server.
4. The **Claude** button appears in the Top Regions panel after any TRIBE
   prediction. First click fires the live API (~10–15 s + poll); subsequent
   toggles on the same text are served from the in-memory cache.

## Bulk pre-ingest (Message Batches API, ~50 % cheaper)

```
python scripts/batch_ingest_claude.py \
    --input modules/ \
    --server http://localhost:8000
```

Supports:
- Directory of `.md`/`.txt` files (each file → one module, `custom_id` =
  filename stem) or a JSON `{custom_id: text}` map.
- `--submit-only` to detach, then `--batch-id <id>` to resume polling later.
- `--output results.json` to save raw Claude outputs alongside the ingest.
- `--no-ingest` to skip pushing to the running server.

Once ingested, every pre-processed module opens instantly in the viewer
(server-side `_result_cache` hit from the first Claude click).

## Cost model

Assumes ~10K input tokens per 20-page module, prompt caching active (~6.9K
static tokens, cached after first call), and Opus 4.7 pricing.

| Thinking budget | Per module (live, cache warm) | 100 modules (live) | 100 modules (batch, -50%) |
|---|---|---|---|
| 0 (disabled) | ~$0.40 | ~$40 | ~$20 |
| 8000 (default) | ~$1.00 | ~$100 | ~$50 |
| 16000 (maximum) | ~$1.60 | ~$160 | ~$80 |

Extended thinking is the single biggest accuracy lever — it lets Claude
reason about register features, within-group peak selection, and coupling
effects before committing to z-scores. Tune via `claude_thinking_budget`
in config (or `--thinking-budget` on the batch script).

## Key files

- `src/htb_brain/core/claude_predictor.py` — Anthropic SDK wrapper (live + batch)
- `src/htb_brain/api/routes/predict_claude.py` — `/api/v1/predict/claude` + `/predict/claude/ingest`
- `docs/claude_predictor_prompt.md` — the cached system prompt (region index, heuristics, schema)
- `scripts/batch_ingest_claude.py` — bulk ingest workflow
- `src/htb_brain/static/brain_viewer/index.html` — 3-state engine toggle (Conservative / Neuroscience / Claude)
