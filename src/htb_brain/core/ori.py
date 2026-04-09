"""Operator Readiness Index (ORI) v4 — four-factor composite score.

Aggregates individual skill mastery data from Algorithm v3.2 into a
composite readiness score (0-100) for high-stakes operational domains.

    ORI = (Mastery × 0.25) + (Currency × 0.30) + (Repetition × 0.25)
        + (Certification × 0.20)

All inputs come from Algorithm v3.2 outputs — peak mastery scores,
health states, total completion counts, and certification records.
The ORI does not modify any Algorithm v3.2 mechanics.
"""

from __future__ import annotations

from htb_brain.core.skill_mastery import SkillMastery

# ---------------------------------------------------------------------------
# ORI factor weights
# ---------------------------------------------------------------------------

WEIGHT_MASTERY = 0.25
WEIGHT_CURRENCY = 0.30
WEIGHT_REPETITION = 0.25
WEIGHT_CERTIFICATION = 0.20

# ---------------------------------------------------------------------------
# Repetition tiers (ORI v4 spec)
# ---------------------------------------------------------------------------

REPETITION_TIERS: list[tuple[int, int]] = [
    (26, 100),
    (11, 85),
    (6, 70),
    (3, 50),
    (1, 25),
    (0, 0),
]


def _repetition_score(total_completions: int) -> int:
    """Map total completions to a repetition tier score (0-100)."""
    for threshold, score in REPETITION_TIERS:
        if total_completions >= threshold:
            return score
    return 0


# ---------------------------------------------------------------------------
# Clearance levels
# ---------------------------------------------------------------------------

CLEARANCE_LEVELS: list[tuple[float, str]] = [
    (70.0, "full"),        # all operations
    (60.0, "limited"),     # supervised operations
    (50.0, "restricted"),  # training only
    (0.0, "grounded"),     # no operations
]

GRADE_SCALE: list[tuple[float, str, str]] = [
    (90.0, "A", "Mission Ready"),
    (80.0, "B", "Fully Operational"),
    (70.0, "C", "Operational"),
    (60.0, "D", "Limited"),
    (50.0, "F", "Remediation"),
    (0.0, "F-", "Grounded"),
]


def clearance_level(ori: float) -> str:
    """Map ORI score to clearance level."""
    for threshold, level in CLEARANCE_LEVELS:
        if ori >= threshold:
            return level
    return "grounded"


def grade(ori: float) -> tuple[str, str]:
    """Map ORI score to (letter_grade, description)."""
    for threshold, letter, desc in GRADE_SCALE:
        if ori >= threshold:
            return letter, desc
    return "F-", "Grounded"


# ---------------------------------------------------------------------------
# ORI calculation
# ---------------------------------------------------------------------------


def calculate_ori(
    skill_masteries: list[SkillMastery],
    required_cert_ids: list[str],
    held_cert_ids: set[str],
) -> dict:
    """Calculate the Operator Readiness Index.

    Args:
        skill_masteries: SkillMastery objects for all required skills.
        required_cert_ids: List of certification IDs required for the role.
        held_cert_ids: Set of certification IDs the operator currently holds.

    Returns:
        Dict with ori score, factors, clearance, grade, and per-skill detail.
    """
    if not skill_masteries:
        return {
            "ori": 0.0,
            "factors": {
                "mastery": 0.0,
                "currency": 0.0,
                "repetition": 0.0,
                "certification": 0.0,
            },
            "clearance": "grounded",
            "grade": "F-",
            "grade_description": "Grounded",
            "total_skills": 0,
        }

    total_skills = len(skill_masteries)

    # ── Factor 1: Mastery (25%) ──────────────────────────────────────────
    # Percentage of required skills at peak = 100 (all three types completed)
    mastered_count = sum(1 for sm in skill_masteries if sm.peak == 100)
    mastery_pct = (mastered_count / total_skills) * 100

    # ── Factor 2: Currency (30%) ─────────────────────────────────────────
    # Percentage of required skills within 120-day window (fresh or at_risk)
    current_count = sum(
        1 for sm in skill_masteries if sm.health in ("fresh", "at_risk")
    )
    currency_pct = (current_count / total_skills) * 100

    # ── Factor 3: Repetition (25%) ───────────────────────────────────────
    # Average repetition tier score across all required skills
    rep_scores = [_repetition_score(sm.total_completions) for sm in skill_masteries]
    repetition_avg = sum(rep_scores) / total_skills

    # ── Factor 4: Certification (20%) ────────────────────────────────────
    # Percentage of required certifications held (binary)
    if required_cert_ids:
        certs_held = sum(1 for cid in required_cert_ids if cid in held_cert_ids)
        cert_pct = (certs_held / len(required_cert_ids)) * 100
    else:
        cert_pct = 100.0  # no certs required = full credit

    # ── Composite ────────────────────────────────────────────────────────
    ori = (
        mastery_pct * WEIGHT_MASTERY
        + currency_pct * WEIGHT_CURRENCY
        + repetition_avg * WEIGHT_REPETITION
        + cert_pct * WEIGHT_CERTIFICATION
    )
    ori = round(ori, 1)

    letter, desc = grade(ori)

    return {
        "ori": ori,
        "factors": {
            "mastery": round(mastery_pct, 1),
            "currency": round(currency_pct, 1),
            "repetition": round(repetition_avg, 1),
            "certification": round(cert_pct, 1),
        },
        "weighted_factors": {
            "mastery": round(mastery_pct * WEIGHT_MASTERY, 1),
            "currency": round(currency_pct * WEIGHT_CURRENCY, 1),
            "repetition": round(repetition_avg * WEIGHT_REPETITION, 1),
            "certification": round(cert_pct * WEIGHT_CERTIFICATION, 1),
        },
        "clearance": clearance_level(ori),
        "grade": letter,
        "grade_description": desc,
        "total_skills": total_skills,
        "mastered_skills": mastered_count,
        "current_skills": current_count,
    }
