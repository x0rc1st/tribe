"""Skill Mastery Algorithm v3.2 — brain-derived completion types.

Implements the full Algorithm v3.2 specification with one change:
course types (Structured/Adaptive/Operational) are replaced by
brain-derived types (Procedural/Analytical/Operational) classified
from TRIBE v2 predictions.  All formulas, constants, and mechanics
are identical to the original spec.

Each skill reaches 100 points through three completion types:
    Procedural  +33  (was Structured)
    Analytical  +33  (was Adaptive)
    Operational +34

Decay: 120-day grace period, then 1 point/week, floor at 20.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from htb_brain.core.completion_classifier import (
    POINTS_ANALYTICAL,
    POINTS_OPERATIONAL,
    POINTS_PROCEDURAL,
)

# ---------------------------------------------------------------------------
# Constants (Algorithm v3.2 Section 11)
# ---------------------------------------------------------------------------

GRACE_PERIOD_DAYS = 120
DECAY_RATE_PER_WEEK = 1
DECAY_FLOOR = 20
AT_RISK_THRESHOLD_DAYS = 7  # days before grace period ends

COMPLETION_TYPES = ("procedural", "analytical", "operational")

TYPE_POINTS: dict[str, int] = {
    "procedural": POINTS_PROCEDURAL,
    "analytical": POINTS_ANALYTICAL,
    "operational": POINTS_OPERATIONAL,
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Completion:
    """A single course/module completion record."""

    course_id: str
    completion_type: str  # 'procedural' | 'analytical' | 'operational'
    skill_tags: list[str]
    date: datetime


@dataclass
class Certification:
    """A certification record."""

    cert_id: str
    skill_tags: list[str]
    date: datetime


@dataclass
class SkillMastery:
    """Mastery state for a single skill (Algorithm v3.2 Section 12)."""

    skill_id: str
    peak: int = 0
    current: int = 0
    completed_types: set[str] = field(default_factory=set)
    total_completions: int = 0
    completions_by_type: dict[str, int] = field(
        default_factory=lambda: {"procedural": 0, "analytical": 0, "operational": 0},
    )
    last_activity: datetime | None = None
    stage: str = "not_started"
    health: str | None = None


# ---------------------------------------------------------------------------
# Core calculation (Algorithm v3.2 Section 13)
# ---------------------------------------------------------------------------


def calculate_skill_mastery(
    skill_id: str,
    completions: list[Completion],
    certifications: list[Certification],
    as_of_date: datetime | None = None,
) -> SkillMastery:
    """Calculate mastery for a single skill.

    Follows Algorithm v3.2 Section 13 exactly:
    - First completion of each type adds points (33/33/34)
    - Order doesn't matter
    - Courses can tag multiple skills
    - All completions tracked for restoration and decay reset
    - Certifications reset decay timer + restore to peak (no points)

    Args:
        skill_id: The skill to calculate mastery for.
        completions: All completion records (will be filtered by skill_tags).
        certifications: All certification records (filtered by skill_tags).
        as_of_date: Point-in-time for decay calculation.  Defaults to now.

    Returns:
        SkillMastery dataclass with full state.
    """
    if as_of_date is None:
        as_of_date = datetime.now(timezone.utc)

    peak = 0
    completed_types: set[str] = set()
    last_activity: datetime | None = None
    total_completions = 0
    completions_by_type = {"procedural": 0, "analytical": 0, "operational": 0}

    # Process completions
    for c in completions:
        if skill_id not in c.skill_tags:
            continue

        total_completions += 1
        completions_by_type[c.completion_type] = (
            completions_by_type.get(c.completion_type, 0) + 1
        )

        # First completion of each type adds points
        if c.completion_type not in completed_types:
            completed_types.add(c.completion_type)
            peak += TYPE_POINTS[c.completion_type]

        # Track last activity
        if last_activity is None or c.date > last_activity:
            last_activity = c.date

    # Process certifications (reset timer, restore to peak, no new points)
    for cert in certifications:
        if skill_id not in cert.skill_tags:
            continue
        if peak == 0:
            continue  # only affects skills already started
        if last_activity is None or cert.date > last_activity:
            last_activity = cert.date

    # Calculate current mastery with decay
    if peak == 0 or last_activity is None:
        current = 0
        health = None
    else:
        days_since = (as_of_date - last_activity).days

        if days_since <= GRACE_PERIOD_DAYS:
            current = peak
            if days_since <= GRACE_PERIOD_DAYS - AT_RISK_THRESHOLD_DAYS:
                health = "fresh"
            else:
                health = "at_risk"
        else:
            weeks_decay = (days_since - GRACE_PERIOD_DAYS) // 7
            current = max(DECAY_FLOOR, peak - weeks_decay * DECAY_RATE_PER_WEEK)
            health = "needs_refresh"

    # Determine stage
    if peak == 0:
        stage = "not_started"
    elif peak < 66:
        stage = "in_progress"
    elif peak < 100:
        stage = "almost_there"
    else:
        stage = "mastered"

    return SkillMastery(
        skill_id=skill_id,
        peak=peak,
        current=current,
        completed_types=completed_types,
        total_completions=total_completions,
        completions_by_type=completions_by_type,
        last_activity=last_activity,
        stage=stage,
        health=health,
    )


# ---------------------------------------------------------------------------
# Batch helper
# ---------------------------------------------------------------------------


def calculate_all_skills(
    skill_ids: list[str],
    completions: list[Completion],
    certifications: list[Certification],
    as_of_date: datetime | None = None,
) -> dict[str, SkillMastery]:
    """Calculate mastery for multiple skills at once."""
    return {
        sid: calculate_skill_mastery(sid, completions, certifications, as_of_date)
        for sid in skill_ids
    }
