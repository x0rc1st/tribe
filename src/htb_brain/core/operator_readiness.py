"""Operator Readiness Profile — 6-dimension scoring engine.

Maps TRIBE v2 brain engagement predictions (10 cortical groups + 7 subcortical
structures) to 6 operator readiness dimensions, each grounded in established
neuroscience and Rasmussen's SRK framework.

Readiness is computed as accumulated signal strength with diminishing returns,
following the power law of practice (Newell & Rosenbloom 1981). Each module's
engagement adds signal; readiness saturates asymptotically toward 1.0.

See docs/operator_readiness_profile.md for the full design document.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

STRONG = 1.0
MODERATE = 0.2   # z > 0.2 ~ 58th percentile — above-average engagement
BASELINE = -0.3

# ---------------------------------------------------------------------------
# Readiness accumulation
# ---------------------------------------------------------------------------

TAU = 2.5  # saturation rate — controls how quickly readiness builds

READINESS_LEVELS = [
    (0.70, "ready"),       # sustained strong engagement
    (0.40, "proficient"),  # solid multi-module engagement
    (0.15, "developing"),  # some engagement, building up
    (0.00, "untrained"),   # little to no engagement
]

GAP_THRESHOLD = 0.15  # readiness below this = gap


def compute_readiness(strengths: list[float]) -> float:
    """Compute readiness from accumulated per-module strength values.

    Uses exponential saturation: readiness = 1 - exp(-raw_signal / tau).
    Each module contributes max(0, strength) — only positive engagement
    counts. Diminishing returns model neural pathway consolidation.

    At tau=2.5:
      1 strong module (z=1.0)  → 33% readiness (developing)
      3 strong modules         → 70% readiness (ready)
      5 strong modules         → 86% readiness (ready)
      Weak modules (z=0.2)     → need ~5 to reach developing
    """
    raw_signal = sum(max(0.0, s) for s in strengths)
    return 1.0 - math.exp(-raw_signal / TAU)


def readiness_level(readiness: float) -> str:
    """Map a readiness score to a human-readable level."""
    for threshold, level in READINESS_LEVELS:
        if readiness >= threshold:
            return level
    return "untrained"


# ---------------------------------------------------------------------------
# Dimension detection (per-module)
# ---------------------------------------------------------------------------


def detect_dimensions(
    group_scores: dict[int, float],
    subcortical: dict[str, dict],
) -> dict[str, dict]:
    """Detect which operator readiness dimensions a piece of content engages.

    Pure prediction-driven: takes TRIBE outputs, returns per-dimension signal.
    The `strength` field reflects the best available signal for how strongly
    this module engaged each dimension's neural circuits.

    Args:
        group_scores: {group_id: z_score} for groups 1-10.
        subcortical: {structure_name: {"z_score": float, "engaged": bool}}.

    Returns:
        {dimension_key: {
            "strength": float,  -- best signal for this dimension
            "srk_mode": str,
            "details": dict,
        }}
    """
    g = group_scores
    sc = subcortical

    dimensions: dict[str, dict] = {}

    # Subcortical direct paths: when a deep brain structure fires at z >= 1.0,
    # it independently contributes strong signal. The structure IS the circuit.
    def _sc_strong(name: str) -> bool:
        s = sc.get(name, {})
        return s.get("engaged", False) and s.get("z_score", -1) >= STRONG

    putamen_or_pallidum = _sc_strong("Putamen") or _sc_strong("Pallidum")
    amygdala_strong = _sc_strong("Amygdala")
    hippo_strong = _sc_strong("Hippocampus")
    amygdala_z = sc.get("Amygdala", {}).get("z_score", 0.0)
    hippo_z = sc.get("Hippocampus", {}).get("z_score", 0.0)

    # 1. Procedural Automaticity (Skill-based)
    g2_val = g.get(2, -1.0)
    g2_ok = g2_val >= MODERATE
    dimensions["procedural_automaticity"] = {
        "strength": g2_val,
        "srk_mode": "skill-based",
        "details": {
            "cortical_motor": g2_val,
            "putamen": sc.get("Putamen", {}).get("z_score", 0.0),
            "pallidum": sc.get("Pallidum", {}).get("z_score", 0.0),
            "subcortical_confirmed": putamen_or_pallidum,
        },
    }

    # 2. Threat Detection & Calibration (Cross-mode)
    # Subcortical (amygdala) determines engagement, cortical (G9) determines strength.
    g9_val = g.get(9, -1.0)
    g9_ok = g9_val >= MODERATE
    dimensions["threat_detection"] = {
        "strength": g9_val,
        "srk_mode": "cross-mode",
        "details": {
            "cortical_threat": g9_val,
            "amygdala": amygdala_z,
            "amygdala_direct": amygdala_strong,
            "motivation": g.get(6, 0.0),
        },
    }

    # 3. Situational Awareness (Rule + Knowledge)
    # Strength reflects all contributing signals, not just the anchor.
    # When comprehension + integration compensate for modest attention,
    # the SA signal is the mean of all three circuits.
    g5_val = g.get(5, -1.0)
    g3_val = g.get(3, -1.0)
    g8_val = g.get(8, -1.0)
    g5_ok = g5_val >= MODERATE
    g3_baseline = g3_val >= BASELINE
    g8_baseline = g8_val >= BASELINE
    g3_mod = g3_val >= MODERATE
    g8_mod = g8_val >= MODERATE
    g5_baseline = g5_val >= BASELINE
    sa_primary = g5_ok and g3_baseline and g8_baseline
    sa_compensated = g5_baseline and g3_mod and g8_mod

    if sa_compensated and not sa_primary:
        sa_strength = (g5_val + g3_val + g8_val) / 3.0
    else:
        sa_strength = g5_val

    dimensions["situational_awareness"] = {
        "strength": sa_strength,
        "srk_mode": "rule-based",
        "details": {
            "attention_focus": g5_val,
            "comprehension": g3_val,
            "integration": g8_val,
            "thalamus": sc.get("Thalamus", {}).get("z_score", 0.0),
            "compensated": sa_compensated and not sa_primary,
        },
    }

    # 4. Strategic Decision-Making & Reflection (Knowledge-based)
    g1_val = g.get(1, -1.0)
    g10_val = g.get(10, -1.0)
    dimensions["strategic_decision"] = {
        "strength": g1_val,
        "srk_mode": "knowledge-based",
        "details": {
            "executive_function": g1_val,
            "reflection": g10_val,
            "caudate_feedback": sc.get("Caudate", {}).get("z_score", 0.0),
        },
    }

    # 5. Analytical Synthesis & Pattern Matching (Knowledge + Rule)
    # Subcortical (hippocampus) determines engagement, cortical (G8) determines strength.
    g8_ok = g8_val >= MODERATE
    g7_val = g.get(7, -1.0)
    g7_ok = g7_val >= BASELINE
    is_adaptive = (g8_ok or hippo_strong) and g1_val >= MODERATE
    dimensions["analytical_synthesis"] = {
        "strength": g8_val,
        "srk_mode": "knowledge-based" if is_adaptive else "rule-based",
        "details": {
            "synthesis": g8_val,
            "memory_encoding": g7_val,
            "hippocampus": hippo_z,
            "hippocampus_direct": hippo_strong,
            "adaptive": is_adaptive,
        },
    }

    # 6. Stress Resilience (All modes under degradation)
    # Strength = min of cognitive and threat CORTICAL peaks.
    # Amygdala determines engagement, but strength comes from cortical signals.
    cognitive_ok = (g1_val >= MODERATE or g5_val >= MODERATE or g8_val >= MODERATE)
    threat_ok = g9_val >= MODERATE or amygdala_strong
    cognitive_peak = max(g1_val, g5_val, g8_val)
    co_active = cognitive_ok and threat_ok
    stress_strength = min(cognitive_peak, g9_val)
    dimensions["stress_resilience"] = {
        "strength": stress_strength,
        "srk_mode": "all-modes-degraded",
        "details": {
            "cognitive_peak": cognitive_peak,
            "threat_activation": g9_val,
            "amygdala_direct": amygdala_strong,
            "co_activation": co_active,
        },
    }

    return dimensions


# ---------------------------------------------------------------------------
# Dependency order (Section 8.2)
# ---------------------------------------------------------------------------

DEPENDENCY_ORDER: dict[str, list[str]] = {
    "stress_resilience": ["procedural_automaticity", "threat_detection"],
    "analytical_synthesis": ["situational_awareness"],
    "strategic_decision": ["analytical_synthesis"],
}

# ---------------------------------------------------------------------------
# Gap messages with SRK error risk (Section 8.1)
# ---------------------------------------------------------------------------

_GAP_CONFIG: dict[str, dict] = {
    "procedural_automaticity": {
        "severity": "critical",
        "srk_error_risk": "Slips and lapses under pressure — correct intention, wrong or skipped action",
        "message": (
            "This operator can explain procedures but hasn't automated them. "
            "Add timed hands-on labs and repetitive drills. "
            "Do NOT advance to stress testing until this is covered."
        ),
        "recommended_content": [
            "Timed CTF labs",
            "Repetitive tool drills",
            "Speed runs",
            "Muscle-memory exercises",
        ],
    },
    "threat_detection": {
        "severity": "critical",
        "srk_error_risk": "Missed threats or alert fatigue — miscalibrated threat reactivity",
        "message": (
            "Training doesn't engage threat detection circuits. "
            "Add escalating threat scenarios and false positive discrimination exercises."
        ),
        "recommended_content": [
            "Escalating scenarios",
            "Red team simulations",
            "False positive discrimination",
            "Mixed benign/malicious analysis",
        ],
    },
    "situational_awareness": {
        "severity": "moderate",
        "srk_error_risk": "Rule-based mistake from lost SA — wrong interpretive frame applied",
        "message": (
            "The operator hasn't practiced maintaining the big picture. "
            "Add multi-host incident scenarios and expanding-scope simulations."
        ),
        "recommended_content": [
            "Multi-host incident scenarios",
            "SOC dashboard exercises",
            "Expanding-scope simulations",
        ],
    },
    "strategic_decision": {
        "severity": "moderate",
        "srk_error_risk": "Knowledge-based mistake — wrong mental model, reasoning from incorrect first principles",
        "message": (
            "Training lacks decision-making under uncertainty. "
            "Add tabletops, incident command sims, and post-incident reviews."
        ),
        "recommended_content": [
            "Tabletop exercises",
            "Incident command simulations",
            "Ambiguous evidence exercises",
            "Post-incident reviews",
        ],
    },
    "analytical_synthesis": {
        "severity": "moderate",
        "srk_error_risk": "Wrong pattern match or failed integration — availability bias or incorrect model",
        "message": (
            "The operator hasn't practiced connecting disparate data. "
            "Add log analysis exercises and attack reconstruction challenges."
        ),
        "recommended_content": [
            "Log analysis",
            "Anomaly detection",
            "Attack reconstruction",
            "Zero-day simulations",
        ],
    },
    "stress_resilience": {
        "severity": "critical",
        "srk_error_risk": "Stress-induced SRK regression — operator drops to lower cognitive mode under pressure",
        "message": (
            "Content doesn't engage cognitive and threat circuits simultaneously. "
            "Add time-pressured CTFs. "
            "NOTE: verify Procedural Automaticity first."
        ),
        "recommended_content": [
            "Time-pressured CTFs with consequences",
            "Inject-based exercises",
            "Chaos engineering",
            "Expanding-scope incidents under ambiguity",
        ],
    },
}

# ---------------------------------------------------------------------------
# Gap detection (readiness-based)
# ---------------------------------------------------------------------------


def detect_gaps(
    dimension_readiness: dict[str, float],
) -> list[dict]:
    """Detect gaps in an operator's readiness profile.

    Args:
        dimension_readiness: {dimension_key: readiness_0_to_1}

    Returns:
        List of DimensionGap dicts, respecting DEPENDENCY_ORDER.
    """
    gaps: list[dict] = []

    for dim_key, config in _GAP_CONFIG.items():
        rdns = dimension_readiness.get(dim_key, 0.0)
        if rdns >= GAP_THRESHOLD:
            continue

        # Check which prerequisite dimensions are also gaps (blocked_by)
        blocked_by: list[str] = []
        for prereq in DEPENDENCY_ORDER.get(dim_key, []):
            if dimension_readiness.get(prereq, 0.0) < GAP_THRESHOLD:
                blocked_by.append(prereq)

        gaps.append({
            "dimension": dim_key,
            "readiness": round(rdns, 3),
            "level": readiness_level(rdns),
            "severity": config["severity"],
            "srk_error_risk": config["srk_error_risk"],
            "blocked_by": blocked_by,
            "recommended_content": config["recommended_content"],
            "message": config["message"],
        })

    # Sort: unblocked first, then by severity
    severity_rank = {"critical": 0, "moderate": 1, "minor": 2}
    gaps.sort(key=lambda g: (len(g["blocked_by"]) > 0, severity_rank.get(g["severity"], 9)))

    return gaps


# ---------------------------------------------------------------------------
# Helper: extract inputs from a predict response
# ---------------------------------------------------------------------------


def extract_readiness_inputs(
    group_scores_list: list[dict],
    subcortical_regions: list[dict],
) -> tuple[dict[int, float], dict[str, dict]]:
    """Convert API response format into detect_dimensions() input format."""
    group_scores = {gs["id"]: gs["z_score"] for gs in group_scores_list}
    subcortical = {}
    for sr in subcortical_regions:
        subcortical[sr["name"]] = {
            "z_score": sr["z_score"],
            "engaged": sr.get("engaged", False),
        }
    return group_scores, subcortical
