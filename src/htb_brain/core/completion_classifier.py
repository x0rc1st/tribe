"""Brain-derived completion type classification.

Replaces manually-labeled course types (Structured/Adaptive/Operational)
from Algorithm v3.2 with a neuroscience-backed classification using the
top activated cognitive groups from TRIBE v2 predictions.

The triangulation is preserved:
    Conceptual (33) + Procedural (33) + Operational (34) = 100 per skill

Classification uses the 3 highest-scoring cognitive groups (by z-score)
from a TRIBE v2 prediction to determine completion type:

    Procedural  — G2 (sensorimotor) in top 3
                  Fitts & Posner cortico-striatal shift

    Conceptual  — G1/G5/G8 (fronto-parietal control network) dominant
                  Klein NDM + Endsley SA

    Operational — G9 (threat) + G1/G5/G8 co-activation in top 3
                  Arnsten prefrontal function under arousal

See docs/ plan for full neuroscience justification of each mapping.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POINTS_CONCEPTUAL = 33   # was POINTS_ADAPTIVE / POINTS_ANALYTICAL
POINTS_PROCEDURAL = 33   # was POINTS_STRUCTURED
POINTS_OPERATIONAL = 34  # unchanged

POINTS = {
    "conceptual": POINTS_CONCEPTUAL,
    "procedural": POINTS_PROCEDURAL,
    "operational": POINTS_OPERATIONAL,
}

# Fronto-parietal control network (Duncan 2010, Cole et al. 2013):
#   G1 — Prefrontal executive (Klein NDM: decision evaluation)
#   G5 — Dorsal parietal attention (Endsley SA: perception-comprehension-projection)
#   G8 — Inferior parietal synthesis (Klein RPD: pattern integration & transfer)
COGNITIVE_GROUPS: frozenset[int] = frozenset({1, 5, 8})

# How many top-scoring groups to consider for classification.
# Top 3 of 10 = top 30%, aligned with standard neuroimaging thresholds.
TOP_N = 3


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def _rank_positive(group_z_scores: dict[int, float]) -> list[tuple[int, float]]:
    return sorted(
        ((gid, z) for gid, z in group_z_scores.items() if z > 0),
        key=lambda x: x[1],
        reverse=True,
    )


def classify_completion(
    group_z_scores: dict[int, float],
    top_n: int = TOP_N,
) -> str:
    """Classify a completion using the top activated brain regions.

    Takes the 10 cognitive group z-scores from a TRIBE v2 prediction
    and returns the completion type for Algorithm v3.2 point assignment.

    The decision priority:
        1. Operational  — G9 (threat) AND G1/G5/G8 both in top N
                          Co-activation = performing under arousal (Arnsten 2009).
        2. Procedural   — G2 (sensorimotor) in top N
                          Motor circuit engagement = building automaticity
                          (Fitts & Posner 1967).
        3. Conceptual   — default (fronto-parietal network or any other pattern)
                          Higher-order cognition without threat co-activation
                          (Klein NDM + Endsley SA).

    Args:
        group_z_scores: {group_id (1-10): z_score} from TRIBE v2 prediction.
        top_n: How many top-ranked positive groups to consider (defaults to TOP_N=3).

    Returns:
        One of ``'procedural'``, ``'conceptual'``, or ``'operational'``.
    """
    top = {gid for gid, _ in _rank_positive(group_z_scores)[:top_n]}

    if 9 in top and top & COGNITIVE_GROUPS:
        return "operational"
    if 2 in top:
        return "procedural"
    return "conceptual"


def classify_completion_detailed(
    group_z_scores: dict[int, float],
    top_n: int = TOP_N,
    group_names: dict[int, str] | None = None,
) -> dict:
    """Classify and return the supporting evidence (rule, top groups, triggers).

    Mirrors ``classify_completion`` but exposes which groups were inspected
    and which decision rule fired so callers can show the user *why*.
    """
    ranked = _rank_positive(group_z_scores)
    top_pairs = ranked[:top_n]
    top_ids = {gid for gid, _ in top_pairs}
    cog_in_top = sorted(top_ids & COGNITIVE_GROUPS)

    if 9 in top_ids and cog_in_top:
        ctype = "operational"
        triggered = [9] + cog_in_top
        rule = (
            "G9 (threat) co-activates with fronto-parietal control "
            f"({', '.join(f'G{g}' for g in cog_in_top)}) — "
            "Arnsten prefrontal-under-arousal."
        )
    elif 2 in top_ids:
        ctype = "procedural"
        triggered = [2]
        rule = (
            "G2 (sensorimotor) is in top groups — "
            "Fitts & Posner motor circuit / habit formation."
        )
    elif cog_in_top:
        ctype = "conceptual"
        triggered = cog_in_top
        rule = (
            "Fronto-parietal control network "
            f"({', '.join(f'G{g}' for g in cog_in_top)}) dominant — "
            "Klein NDM + Endsley SA."
        )
    else:
        ctype = "conceptual"
        triggered = sorted(top_ids)
        rule = (
            "No threat / sensorimotor / fronto-parietal markers in top groups — "
            "default to conceptual."
        )

    names = group_names or {}
    return {
        "type": ctype,
        "top_n": top_n,
        "rule": rule,
        "triggered_group_ids": triggered,
        "top_groups": [
            {"id": gid, "name": names.get(gid, f"G{gid}"), "z_score": float(z)}
            for gid, z in top_pairs
        ],
    }


def completion_points(completion_type: str) -> int:
    """Return the mastery points for a completion type."""
    return POINTS[completion_type]
