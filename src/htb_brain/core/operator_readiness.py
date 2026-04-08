"""Operator Readiness Profile — 6-dimension scoring engine.

Maps TRIBE v2 brain engagement predictions (10 cortical groups + 7 subcortical
structures) to 6 operator readiness dimensions, each grounded in established
neuroscience and Rasmussen's SRK framework.

Scoring model:
  1. Per module: strength = weighted sum of positive group z-scores
  2. Per operator: readiness = 1 - exp(-sum(strengths) / tau)

No binary gates, no thresholds in strength calculation. Every positive
signal contributes proportionally. Readiness accumulates with diminishing
returns (power law of practice, Newell & Rosenbloom 1981).

See docs/operator_readiness_profile.md for the full design document.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Readiness accumulation
# ---------------------------------------------------------------------------

TAU = 20.0  # calibrated to HTB paths: ~18 modules + ~18 labs + team exercise

READINESS_LEVELS = [
    (0.70, "saturated"),    # extensive exposure, diminishing returns from more of the same
    (0.40, "substantial"),  # significant training signal accumulated
    (0.15, "building"),     # accumulating exposure, early training
    (0.00, "minimal"),      # barely exposed to this dimension
]

GAP_THRESHOLD = 0.15  # readiness below this = gap


def compute_readiness(strengths: list[float]) -> float:
    """Compute readiness from accumulated per-module strength values.

    Uses exponential saturation: readiness = 1 - exp(-raw_signal / tau).
    Diminishing returns model neural pathway consolidation.

    Calibrated to HTB learning paths (~18 modules + ~18 labs + team ex):
      After theory modules (~18×0.3) →  24% (building)
      After theory + labs (~36×avg)  →  56% (substantial)
      After full path + team ex      →  57% (substantial)
      After 2 full paths             →  82% (saturated)
    """
    raw_signal = sum(strengths)  # strengths are already non-negative
    return 1.0 - math.exp(-raw_signal / TAU)


def readiness_level(readiness: float) -> str:
    """Map a readiness score to a human-readable level."""
    for threshold, level in READINESS_LEVELS:
        if readiness >= threshold:
            return level
    return "untrained"


# ---------------------------------------------------------------------------
# Dimension signal weights
#
# Each dimension defines which cortical groups contribute and at what weight.
# Anchor group gets 0.6, supporting groups split the remaining 0.4.
# Weights are derived from the neuroscience mapping in the design doc.
# ---------------------------------------------------------------------------

DIM_WEIGHTS: dict[str, dict[int, float]] = {
    # Anchor: G2 (sensorimotor). No cortical supporting groups.
    "procedural_automaticity": {2: 1.0},

    # Anchor: G9 (insular/threat). No cortical supporting groups.
    "threat_detection": {9: 1.0},

    # Anchor: G5 (dorsal parietal attention). Supports: G3 (comprehension), G8 (integration).
    # Maps to Endsley's 3 SA levels: perception(G5), comprehension(G3), projection(G8).
    "situational_awareness": {5: 0.5, 3: 0.25, 8: 0.25},

    # Anchor: G1 (prefrontal executive). Supports: G10 (reflective/DMN).
    # Maps to Klein's NDM: decide(G1) + reflect(G10).
    "strategic_decision": {1: 0.6, 10: 0.4},

    # Anchor: G8 (inferior parietal synthesis). Supports: G7 (memory encoding).
    # Maps to Klein's RPD: integrate(G8) + bind(G7).
    "analytical_synthesis": {8: 0.6, 7: 0.4},

    # Stress resilience is computed separately (co-activation).
}

# SRK mode labels (informational, from Rasmussen's framework)
DIM_SRK = {
    "procedural_automaticity": "skill-based",
    "threat_detection": "cross-mode",
    "situational_awareness": "rule-based",
    "strategic_decision": "knowledge-based",
    "analytical_synthesis": "rule-based",
    "stress_resilience": "all-modes-degraded",
}


# ---------------------------------------------------------------------------
# Dimension scoring (per module)
# ---------------------------------------------------------------------------


def _weighted_strength(weights: dict[int, float], g: dict[int, float]) -> float:
    """Weighted sum of positive group z-scores."""
    return sum(w * max(0.0, g.get(gid, 0.0)) for gid, w in weights.items())


def detect_dimensions(
    group_scores: dict[int, float],
    subcortical: dict[str, dict],
) -> dict[str, dict]:
    """Compute per-dimension strength for a single module.

    Strength = weighted sum of positive cortical z-scores.
    No binary gates or thresholds — every positive signal contributes
    proportionally to the dimension's weight map.

    Args:
        group_scores: {group_id: z_score} for groups 1-10.
        subcortical: {structure_name: {"z_score": float, "engaged": bool}}.

    Returns:
        {dimension_key: {"strength": float, "srk_mode": str, "details": dict}}
    """
    g = group_scores
    sc = subcortical
    dimensions: dict[str, dict] = {}

    # Standard dimensions: weighted positive signals
    for dim_key, weights in DIM_WEIGHTS.items():
        strength = _weighted_strength(weights, g)

        details: dict = {}
        for gid, w in weights.items():
            details["g%d" % gid] = g.get(gid, 0.0)
            details["g%d_weight" % gid] = w
            details["g%d_contribution" % gid] = round(w * max(0.0, g.get(gid, 0.0)), 4)

        # Add relevant subcortical info
        if dim_key == "procedural_automaticity":
            details["putamen"] = sc.get("Putamen", {}).get("z_score", 0.0)
            details["pallidum"] = sc.get("Pallidum", {}).get("z_score", 0.0)
        elif dim_key == "threat_detection":
            details["amygdala"] = sc.get("Amygdala", {}).get("z_score", 0.0)
        elif dim_key == "situational_awareness":
            details["thalamus"] = sc.get("Thalamus", {}).get("z_score", 0.0)
        elif dim_key == "strategic_decision":
            details["caudate"] = sc.get("Caudate", {}).get("z_score", 0.0)
        elif dim_key == "analytical_synthesis":
            details["hippocampus"] = sc.get("Hippocampus", {}).get("z_score", 0.0)

        dimensions[dim_key] = {
            "strength": round(strength, 4),
            "srk_mode": DIM_SRK[dim_key],
            "details": details,
        }

    # Stress Resilience: co-activation of cognitive + threat.
    # Strength = min(cognitive_peak, threat) — limited by the weaker side.
    # Both must be positive for any contribution.
    cognitive = max(
        max(0.0, g.get(1, 0.0)),
        max(0.0, g.get(5, 0.0)),
        max(0.0, g.get(8, 0.0)),
    )
    threat = max(0.0, g.get(9, 0.0))
    stress_strength = min(cognitive, threat)

    dimensions["stress_resilience"] = {
        "strength": round(stress_strength, 4),
        "srk_mode": DIM_SRK["stress_resilience"],
        "details": {
            "cognitive_peak": round(cognitive, 4),
            "cognitive_source": {
                "g1": g.get(1, 0.0),
                "g5": g.get(5, 0.0),
                "g8": g.get(8, 0.0),
            },
            "threat": round(threat, 4),
            "g9": g.get(9, 0.0),
            "amygdala": sc.get("Amygdala", {}).get("z_score", 0.0),
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
