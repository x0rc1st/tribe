"""Brain-derived completion type classification.

Replaces manually-labeled course types (Structured/Adaptive/Operational)
from Algorithm v3.2 with a neuroscience-backed classification using the
top activated cognitive groups from TRIBE v2 predictions.

The triangulation is preserved:
    Procedural (33) + Analytical (33) + Operational (34) = 100 per skill

Classification uses the 3 highest-scoring cognitive groups (by z-score)
from a TRIBE v2 prediction to determine completion type:

    Procedural  — G2 (sensorimotor) in top 3
                  Fitts & Posner cortico-striatal shift

    Analytical  — G1/G5/G8 (fronto-parietal control network) dominant
                  Klein NDM + Endsley SA

    Operational — G9 (threat) + G1/G5/G8 co-activation in top 3
                  Arnsten prefrontal function under arousal

See docs/ plan for full neuroscience justification of each mapping.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POINTS_PROCEDURAL = 33   # was POINTS_STRUCTURED
POINTS_ANALYTICAL = 33   # was POINTS_ADAPTIVE
POINTS_OPERATIONAL = 34  # unchanged

POINTS = {
    "procedural": POINTS_PROCEDURAL,
    "analytical": POINTS_ANALYTICAL,
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


def classify_completion(group_z_scores: dict[int, float]) -> str:
    """Classify a completion using the top activated brain regions.

    Takes the 10 cognitive group z-scores from a TRIBE v2 prediction
    and returns the completion type for Algorithm v3.2 point assignment.

    The decision priority:
        1. Operational  — G9 (threat) AND G1/G5/G8 both in top 3
                          Co-activation = performing under arousal (Arnsten 2009).
        2. Procedural   — G2 (sensorimotor) in top 3
                          Motor circuit engagement = building automaticity
                          (Fitts & Posner 1967).
        3. Analytical    — default (fronto-parietal network or any other pattern)
                          Higher-order cognition without threat co-activation
                          (Klein NDM + Endsley SA).

    Args:
        group_z_scores: {group_id (1-10): z_score} from TRIBE v2 prediction.

    Returns:
        One of ``'procedural'``, ``'analytical'``, or ``'operational'``.
    """
    # Rank groups by z-score, keep only positive activations
    ranked = sorted(
        ((gid, z) for gid, z in group_z_scores.items() if z > 0),
        key=lambda x: x[1],
        reverse=True,
    )
    top = {gid for gid, _ in ranked[:TOP_N]}

    # 1. Operational: threat + executive co-activation in top regions.
    #    Arnsten mechanism — prefrontal must be active WHILE threat circuit
    #    fires.  G2+G9 without cognitive groups is stress-induced SRK
    #    regression (a failure mode), not operational readiness.
    if 9 in top and top & COGNITIVE_GROUPS:
        return "operational"

    # 2. Procedural: sensorimotor dominant.
    #    Fitts & Posner — content engages motor planning, action sequencing,
    #    and procedural memory (putamen/pallidum habit formation).
    if 2 in top:
        return "procedural"

    # 3. Analytical: fronto-parietal control network or any remaining pattern.
    #    Klein NDM + Endsley SA.  Also the correct default when top groups
    #    are G3 (language), G4 (visual), G6 (motivation), G7 (memory),
    #    or G10 (reflective) — all represent conceptual/knowledge learning.
    return "analytical"


def completion_points(completion_type: str) -> int:
    """Return the mastery points for a completion type."""
    return POINTS[completion_type]
