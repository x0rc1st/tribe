"""Operator Readiness Profile — 6-dimension scoring engine.

Maps TRIBE v2 brain engagement predictions (10 cortical groups + 7 subcortical
structures) to 6 operator readiness dimensions, each grounded in established
neuroscience and Rasmussen's SRK framework.

Detection is driven purely by prediction outputs — no modality awareness.

See docs/operator_readiness_profile.md for the full design document.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

STRONG = 1.0
MODERATE = 0.2   # z > 0.2 ≈ 58th percentile — above-average engagement
BASELINE = -0.3

# ---------------------------------------------------------------------------
# Dimension detection
# ---------------------------------------------------------------------------


def detect_dimensions(
    group_scores: dict[int, float],
    subcortical: dict[str, dict],
) -> dict[str, dict]:
    """Detect which operator readiness dimensions a piece of content covers.

    Pure prediction-driven: takes TRIBE outputs, returns dimension coverage.
    No modality awareness — the model's predictions are the signal.

    Args:
        group_scores: {group_id: z_score} for groups 1-10.
        subcortical: {structure_name: {"z_score": float, "engaged": bool}}.

    Returns:
        {dimension_key: {
            "covered": bool,
            "strength": float,
            "srk_mode": str,
            "details": dict,
        }}
    """
    g = group_scores
    sc = subcortical

    dimensions: dict[str, dict] = {}

    # Subcortical direct paths: when a deep brain structure fires at z >= 1.0,
    # it independently triggers the dimension. The structure IS the circuit.
    def _sc_strong(name: str) -> bool:
        s = sc.get(name, {})
        return s.get("engaged", False) and s.get("z_score", -1) >= STRONG

    putamen_or_pallidum = _sc_strong("Putamen") or _sc_strong("Pallidum")
    amygdala_strong = _sc_strong("Amygdala")
    hippo_strong = _sc_strong("Hippocampus")
    amygdala_z = sc.get("Amygdala", {}).get("z_score", 0.0)
    hippo_z = sc.get("Hippocampus", {}).get("z_score", 0.0)

    # 1. Procedural Automaticity (Skill-based)
    g2_ok = g.get(2, -1) >= MODERATE
    dimensions["procedural_automaticity"] = {
        "covered": g2_ok or putamen_or_pallidum,
        "strength": g.get(2, 0.0),
        "srk_mode": "skill-based",
        "details": {
            "cortical_motor": g.get(2, 0.0),
            "putamen": sc.get("Putamen", {}).get("z_score", 0.0),
            "pallidum": sc.get("Pallidum", {}).get("z_score", 0.0),
            "subcortical_confirmed": putamen_or_pallidum,
        },
    }

    # 2. Threat Detection & Calibration (Cross-mode)
    g9_ok = g.get(9, -1) >= MODERATE
    dimensions["threat_detection"] = {
        "covered": g9_ok or amygdala_strong,
        "strength": max(g.get(9, 0.0), amygdala_z) if amygdala_strong else g.get(9, 0.0),
        "srk_mode": "cross-mode",
        "details": {
            "cortical_threat": g.get(9, 0.0),
            "amygdala": amygdala_z,
            "amygdala_direct": amygdala_strong,
            "motivation": g.get(6, 0.0),
        },
    }

    # 3. Situational Awareness (Rule + Knowledge)
    g5_ok = g.get(5, -1) >= MODERATE
    g3_ok = g.get(3, -1) >= BASELINE
    g8_baseline = g.get(8, -1) >= BASELINE
    dimensions["situational_awareness"] = {
        "covered": g5_ok and g3_ok and g8_baseline,
        "strength": g.get(5, 0.0),
        "srk_mode": "rule-based",
        "details": {
            "attention_focus": g.get(5, 0.0),
            "comprehension": g.get(3, 0.0),
            "integration": g.get(8, 0.0),
            "thalamus": sc.get("Thalamus", {}).get("z_score", 0.0),
        },
    }

    # 4. Strategic Decision-Making & Reflection (Knowledge-based)
    g1_ok = g.get(1, -1) >= MODERATE
    g10_ok = g.get(10, -1) >= BASELINE
    dimensions["strategic_decision"] = {
        "covered": g1_ok and g10_ok,
        "strength": g.get(1, 0.0),
        "srk_mode": "knowledge-based",
        "details": {
            "executive_function": g.get(1, 0.0),
            "reflection": g.get(10, 0.0),
            "caudate_feedback": sc.get("Caudate", {}).get("z_score", 0.0),
        },
    }

    # 5. Analytical Synthesis & Pattern Matching (Knowledge + Rule)
    g8_ok = g.get(8, -1) >= MODERATE
    g7_ok = g.get(7, -1) >= BASELINE
    is_adaptive = (g8_ok or hippo_strong) and g.get(1, -1) >= MODERATE
    dimensions["analytical_synthesis"] = {
        "covered": (g8_ok and g7_ok) or (hippo_strong and g7_ok),
        "strength": max(g.get(8, 0.0), hippo_z) if hippo_strong else g.get(8, 0.0),
        "srk_mode": "knowledge-based" if is_adaptive else "rule-based",
        "details": {
            "synthesis": g.get(8, 0.0),
            "memory_encoding": g.get(7, 0.0),
            "hippocampus": hippo_z,
            "hippocampus_direct": hippo_strong,
            "adaptive": is_adaptive,
        },
    }

    # 6. Stress Resilience (All modes under degradation)
    cognitive_ok = (
        g.get(1, -1) >= MODERATE
        or g.get(5, -1) >= MODERATE
        or g.get(8, -1) >= MODERATE
    )
    threat_ok = g.get(9, -1) >= MODERATE or amygdala_strong
    cognitive_peak = max(g.get(1, -1), g.get(5, -1), g.get(8, -1))
    threat_peak = max(g.get(9, -1), amygdala_z) if amygdala_strong else g.get(9, -1)
    dimensions["stress_resilience"] = {
        "covered": cognitive_ok and threat_ok,
        "strength": min(cognitive_peak, threat_peak),
        "srk_mode": "all-modes-degraded",
        "details": {
            "cognitive_peak": cognitive_peak,
            "threat_activation": g.get(9, 0.0),
            "amygdala_direct": amygdala_strong,
            "co_activation": cognitive_ok and threat_ok,
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
# Gap detection
# ---------------------------------------------------------------------------


def detect_gaps(
    dimension_coverage: dict[str, float],
) -> list[dict]:
    """Detect gaps in an operator's readiness profile.

    Args:
        dimension_coverage: {dimension_key: coverage_float_0_to_1}
            from the accumulated operator profile.

    Returns:
        List of DimensionGap dicts, respecting DEPENDENCY_ORDER.
    """
    COVERAGE_THRESHOLD = 0.3  # below this = gap

    gaps: list[dict] = []

    for dim_key, config in _GAP_CONFIG.items():
        coverage = dimension_coverage.get(dim_key, 0.0)
        if coverage >= COVERAGE_THRESHOLD:
            continue

        # Check which prerequisite dimensions are also gaps (blocked_by)
        blocked_by: list[str] = []
        for prereq in DEPENDENCY_ORDER.get(dim_key, []):
            prereq_coverage = dimension_coverage.get(prereq, 0.0)
            if prereq_coverage < COVERAGE_THRESHOLD:
                blocked_by.append(prereq)

        gaps.append({
            "dimension": dim_key,
            "current_coverage": round(coverage, 3),
            "severity": config["severity"],
            "srk_error_risk": config["srk_error_risk"],
            "blocked_by": blocked_by,
            "recommended_content": config["recommended_content"],
            "message": config["message"],
        })

    # Sort: unblocked gaps first, then by severity (critical > moderate)
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
    """Convert API response format into detect_dimensions() input format.

    Args:
        group_scores_list: List of GroupScoreResponse dicts from predict.
        subcortical_regions: List of SubcorticalRegionResponse dicts.

    Returns:
        (group_scores_dict, subcortical_dict) ready for detect_dimensions().
    """
    group_scores = {gs["id"]: gs["z_score"] for gs in group_scores_list}

    subcortical = {}
    for sr in subcortical_regions:
        subcortical[sr["name"]] = {
            "z_score": sr["z_score"],
            "engaged": sr.get("engaged", False),
        }

    return group_scores, subcortical
