"""ClaudePredictor — a third prediction mode that bypasses TRIBE entirely.

Given a learning-module text, calls the Anthropic API (Opus 4.7 by default)
with the neuroscience-grounded system prompt in `docs/claude_predictor_prompt.md`
and returns per-Destrieux-region z-scores + per-Harvard-Oxford-structure
z-scores. The route layer (`predict_claude.py`) then feeds those z-scores
through the same downstream pipeline that runs on real TRIBE output, so the
final response shape is byte-compatible with the TRIBE path.

Supports two call modes:
- `predict(text)` — live API, ~10 s per call, used by the viewer toggle
- `submit_batch(texts)` / `poll_batch(...)` — Message Batches API, ~24 h
  turnaround at 50 % cost, used by `scripts/batch_ingest_claude.py`
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "docs"
    / "claude_predictor_prompt.md"
)


def _load_system_prompt() -> str:
    """Extract the prompt body (between the outer ``` fences) from the markdown doc."""
    raw = _PROMPT_PATH.read_text(encoding="utf-8")
    # The file wraps the actual prompt in a single top-level ``` fence.
    # Grab the largest fenced block.
    matches = re.findall(r"```\n(.*?)\n```", raw, flags=re.DOTALL)
    if not matches:
        raise RuntimeError(
            f"No fenced prompt block found in {_PROMPT_PATH}. "
            "Expected the prompt body wrapped in ``` fences."
        )
    # Use the largest block (the prompt body).
    return max(matches, key=len)


# Expected keys in Claude's response — derived from the output schema in the
# prompt. These are also the exact atlas identifiers Translator/aggregator use.
CORTICAL_KEYS: tuple[str, ...] = (
    # G1 Strategic
    "G_front_sup", "G_front_middle", "G_front_inf-Triangul", "G_front_inf-Orbital",
    "G_orbital", "G_rectus", "G_and_S_frontomargin", "G_and_S_transv_frontopol",
    "S_front_sup", "S_front_middle", "S_front_inf", "S_orbital_lateral",
    "S_orbital_med-olfact", "S_orbital-H_Shaped", "S_suborbital",
    # G2 Procedural
    "G_precentral", "G_postcentral", "G_and_S_paracentral", "G_and_S_subcentral",
    "S_central", "S_precentral-inf-part", "S_precentral-sup-part", "S_postcentral",
    # G3 Language
    "G_front_inf-Opercular", "G_temp_sup-Lateral", "G_temp_sup-Plan_tempo",
    "G_temp_sup-Plan_polar", "G_temp_sup-G_T_transv", "G_temporal_middle",
    "S_temporal_sup", "S_temporal_transverse", "Lat_Fis-ant-Horizont",
    "Lat_Fis-ant-Vertical", "Lat_Fis-post",
    # G4 Visual
    "G_cuneus", "G_occipital_sup", "G_occipital_middle", "G_and_S_occipital_inf",
    "Pole_occipital", "G_oc-temp_lat-fusifor", "G_oc-temp_med-Lingual",
    "G_temporal_inf", "S_calcarine", "S_occipital_ant", "S_oc_middle_and_Lunatus",
    "S_oc_sup_and_transversal", "S_oc-temp_lat", "S_oc-temp_med_and_Lingual",
    "S_temporal_inf", "S_parieto_occipital",
    # G5 Situational awareness
    "G_parietal_sup", "S_intrapariet_and_P_trans", "S_subparietal",
    # G6 Motivation
    "G_and_S_cingul-Ant", "G_and_S_cingul-Mid-Ant", "G_and_S_cingul-Mid-Post",
    "S_cingul-Marginalis", "S_pericallosal",
    # G7 Memory
    "G_oc-temp_med-Parahip", "Pole_temporal", "S_collat_transv_ant", "S_collat_transv_post",
    # G8 Synthesis
    "G_pariet_inf-Angular", "G_pariet_inf-Supramar", "S_interm_prim-Jensen",
    # G9 Threat
    "G_insular_short", "G_Ins_lg_and_S_cent_ins", "S_circular_insula_ant",
    "S_circular_insula_inf", "S_circular_insula_sup",
    # G10 Reflective
    "G_cingul-Post-dorsal", "G_cingul-Post-ventral", "G_precuneus", "G_subcallosal",
)

SUBCORTICAL_KEYS: tuple[str, ...] = (
    "Thalamus", "Caudate", "Putamen", "Pallidum",
    "Hippocampus", "Amygdala", "Accumbens",
)


class ClaudePredictionError(RuntimeError):
    """Raised when the Anthropic response cannot be parsed into the expected schema."""


class ClaudePredictor:
    """Neuroscience-grounded emulator of TRIBE v2, backed by Claude."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-4-7",
        max_tokens: int = 4096,
        thinking_budget: int = 8000,
    ):
        if not api_key:
            raise ValueError(
                "Anthropic API key is required. Set HTB_BRAIN_ANTHROPIC_API_KEY or "
                "ANTHROPIC_API_KEY in your environment."
            )
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.thinking_budget = thinking_budget  # 0 = disabled
        self._system_prompt: str | None = None
        self._client = None

    def _thinking_kwargs(self) -> dict:
        """Assemble the kwargs for a messages.create call that control extended
        thinking and the effective output budget.

        Extended thinking consumes output-rate tokens before Claude emits its
        JSON — the `budget_tokens` is a target, not a hard cap. `max_tokens`
        on the request is the total ceiling (thinking + visible output), so
        we expand it when thinking is enabled to leave headroom for the JSON.
        """
        if self.thinking_budget > 0:
            return {
                "max_tokens": self.max_tokens + self.thinking_budget,
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": self.thinking_budget,
                },
                # Extended thinking requires temperature=1; leave top_p/top_k unset.
                "temperature": 1.0,
            }
        return {"max_tokens": self.max_tokens}

    @staticmethod
    def _extract_text_block(content_blocks) -> str:
        """Pull the visible text from a response, skipping thinking blocks.

        When extended thinking is enabled, the response `content` list contains
        one or more `ThinkingBlock`s followed by the final `TextBlock`. Only
        the latter carries the JSON we need.
        """
        for block in content_blocks:
            btype = getattr(block, "type", None)
            if btype == "text":
                return getattr(block, "text", "") or ""
        # Fallback for older SDKs or unexpected shapes.
        if content_blocks and hasattr(content_blocks[0], "text"):
            return content_blocks[0].text or ""
        return ""

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def _get_system_prompt(self) -> str:
        if self._system_prompt is None:
            self._system_prompt = _load_system_prompt()
            logger.info(
                "Claude predictor prompt loaded (%d chars, ~%d tokens)",
                len(self._system_prompt),
                len(self._system_prompt) // 4,
            )
        return self._system_prompt

    # --- Live API ---------------------------------------------------------

    def predict(self, text: str) -> dict[str, Any]:
        """Run a live prediction. Returns parsed z-score dicts.

        Returns:
            {
                "reasoning": str,
                "cortical_region_zscores": {region: z_score, ...},
                "subcortical_region_zscores": {region: z_score, ...},
            }
        """
        client = self._get_client()
        system = self._get_system_prompt()
        user_text = self._build_user_message(text)

        logger.info(
            "Submitting Claude prediction (model=%s, text=%d chars, thinking=%d)",
            self.model, len(text), self.thinking_budget,
        )
        resp = client.messages.create(
            model=self.model,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_text}],
            **self._thinking_kwargs(),
        )

        raw_text = self._extract_text_block(resp.content)
        parsed = self._parse_response(raw_text)

        usage = getattr(resp, "usage", None)
        if usage is not None:
            logger.info(
                "Claude usage: input=%s cache_read=%s cache_create=%s output=%s",
                getattr(usage, "input_tokens", None),
                getattr(usage, "cache_read_input_tokens", None),
                getattr(usage, "cache_creation_input_tokens", None),
                getattr(usage, "output_tokens", None),
            )

        return parsed

    # --- Batch API --------------------------------------------------------

    def submit_batch(self, items: list[tuple[str, str]]) -> str:
        """Submit a Message Batches API job.

        Args:
            items: list of (custom_id, text) tuples — one per module.

        Returns:
            batch_id (message-batches ID for polling).
        """
        client = self._get_client()
        system = self._get_system_prompt()

        from anthropic.types.messages.batch_create_params import Request
        from anthropic.types.message_create_params import MessageCreateParamsNonStreaming

        thinking_kwargs = self._thinking_kwargs()
        requests = []
        for custom_id, text in items:
            user_text = self._build_user_message(text)
            requests.append(
                Request(
                    custom_id=custom_id,
                    params=MessageCreateParamsNonStreaming(
                        model=self.model,
                        system=[
                            {
                                "type": "text",
                                "text": system,
                                "cache_control": {"type": "ephemeral"},
                            }
                        ],
                        messages=[{"role": "user", "content": user_text}],
                        **thinking_kwargs,
                    ),
                )
            )

        logger.info(
            "Submitting batch of %d modules (model=%s, thinking=%d)",
            len(requests), self.model, self.thinking_budget,
        )
        batch = client.messages.batches.create(requests=requests)
        logger.info("Batch submitted: id=%s status=%s", batch.id, batch.processing_status)
        return batch.id

    def poll_batch(self, batch_id: str) -> dict[str, Any]:
        """Check the status of a batch job.

        Returns:
            {
                "status": "in_progress" | "ended" | "canceling" | "canceled" | "expired",
                "request_counts": {...},
                "ended_at": str | None,
            }
        """
        client = self._get_client()
        batch = client.messages.batches.retrieve(batch_id)
        return {
            "status": batch.processing_status,
            "request_counts": dict(batch.request_counts.__dict__)
            if hasattr(batch.request_counts, "__dict__")
            else {},
            "ended_at": str(batch.ended_at) if batch.ended_at else None,
        }

    def fetch_batch_results(self, batch_id: str) -> dict[str, dict[str, Any]]:
        """Fetch completed batch results. Only call after poll_batch returns 'ended'.

        Returns:
            {custom_id: parsed_prediction, ...}
        """
        client = self._get_client()
        results: dict[str, dict[str, Any]] = {}
        for result in client.messages.batches.results(batch_id):
            cid = result.custom_id
            if result.result.type != "succeeded":
                logger.warning("Batch item %s failed: %s", cid, result.result.type)
                continue
            msg = result.result.message
            raw_text = self._extract_text_block(msg.content)
            try:
                results[cid] = self._parse_response(raw_text)
            except ClaudePredictionError:
                logger.exception("Could not parse Claude response for %s", cid)
        return results

    # --- Helpers ----------------------------------------------------------

    @staticmethod
    def _build_user_message(text: str) -> str:
        # The prompt template has `{{MODULE_TEXT}}` in a <source> tag, but we
        # pass the system prompt fixed and put the text in the user turn. The
        # `<source>` tag at the end of the system prompt is a placeholder; we
        # substitute it at user-message construction time with a short pointer
        # and include the actual text in the user turn for clearer separation
        # and better caching.
        return (
            "Here is the learning module to predict on. Respond with the JSON "
            "object specified by the output schema — no prose outside the "
            "JSON, no markdown fences.\n\n"
            f"<module>\n{text}\n</module>"
        )

    @staticmethod
    def _parse_response(raw_text: str) -> dict[str, Any]:
        """Parse Claude's JSON output, tolerating surrounding noise."""
        raw = raw_text.strip()

        # Strip a ```json fence if the model slipped one in.
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\n", "", raw)
            raw = re.sub(r"\n```$", "", raw)

        # Grab the outermost {...} block if there's still surrounding prose.
        first_brace = raw.find("{")
        last_brace = raw.rfind("}")
        if first_brace == -1 or last_brace == -1 or last_brace < first_brace:
            raise ClaudePredictionError(
                f"No JSON object found in Claude response. Raw: {raw_text[:500]!r}"
            )
        json_text = raw[first_brace : last_brace + 1]

        try:
            obj = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ClaudePredictionError(
                f"Could not parse JSON from Claude response: {e}. Raw: {raw_text[:500]!r}"
            ) from e

        cortical = obj.get("cortical_region_zscores") or {}
        subcortical = obj.get("subcortical_region_zscores") or {}

        missing_cort = [k for k in CORTICAL_KEYS if k not in cortical]
        missing_sub = [k for k in SUBCORTICAL_KEYS if k not in subcortical]
        if missing_cort or missing_sub:
            raise ClaudePredictionError(
                f"Claude response is missing required keys. "
                f"Missing cortical: {missing_cort[:5]}{'...' if len(missing_cort) > 5 else ''}. "
                f"Missing subcortical: {missing_sub}."
            )

        # Coerce to floats; drop unexpected extra keys silently (schema discipline).
        cortical_clean = {k: float(cortical[k]) for k in CORTICAL_KEYS}
        subcortical_clean = {k: float(subcortical[k]) for k in SUBCORTICAL_KEYS}

        return {
            "reasoning": obj.get("reasoning", ""),
            "cortical_region_zscores": cortical_clean,
            "subcortical_region_zscores": subcortical_clean,
        }
