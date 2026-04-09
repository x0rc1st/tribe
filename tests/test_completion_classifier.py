"""Tests for brain-derived completion classification.

Verifies that classify_completion() correctly maps TRIBE v2 cognitive
group z-scores to Algorithm v3.2 completion types (procedural,
analytical, operational) using the top-3 brain region logic.
"""

import pytest

from htb_brain.core.completion_classifier import (
    COGNITIVE_GROUPS,
    POINTS_ANALYTICAL,
    POINTS_OPERATIONAL,
    POINTS_PROCEDURAL,
    TOP_N,
    classify_completion,
    completion_points,
)


def _scores(**overrides: float) -> dict[int, float]:
    """Build a group_z_scores dict with defaults at 0 and overrides by group id.

    Usage: _scores(g2=1.5, g1=0.8) → {1: 0.8, 2: 1.5, 3: 0, ...}
    """
    base = {i: 0.0 for i in range(1, 11)}
    for key, val in overrides.items():
        gid = int(key.lstrip("g"))
        base[gid] = val
    return base


# =====================================================================
# Procedural classification (G2 in top 3)
# =====================================================================

class TestProcedural:
    """G2 (sensorimotor) in top 3 → procedural."""

    def test_g2_dominant(self):
        """G2 is the strongest group → procedural."""
        scores = _scores(g2=2.0, g3=0.5, g4=0.3)
        assert classify_completion(scores) == "procedural"

    def test_g2_third_in_top3(self):
        """G2 is 3rd in top 3 (behind non-marker groups) → procedural."""
        scores = _scores(g3=2.0, g7=1.5, g2=1.0)
        assert classify_completion(scores) == "procedural"

    def test_g2_with_g1(self):
        """G2 + G1 both in top 3 (associative stage) → procedural.

        Fitts & Posner associative stage: motor cortex + prefrontal.
        Without G9, this is procedural, not operational.
        """
        scores = _scores(g1=1.5, g2=1.8, g3=0.5)
        assert classify_completion(scores) == "procedural"

    def test_g2_with_g5(self):
        """G2 + G5 without G9 → procedural (motor + attention, no threat)."""
        scores = _scores(g2=1.5, g5=1.2, g4=0.8)
        assert classify_completion(scores) == "procedural"


# =====================================================================
# Analytical classification (G1/G5/G8 dominant or default)
# =====================================================================

class TestAnalytical:
    """G1/G5/G8 dominant or default → analytical."""

    def test_g1_dominant(self):
        """G1 (prefrontal executive) dominant → analytical."""
        scores = _scores(g1=2.0, g3=1.0, g7=0.5)
        assert classify_completion(scores) == "analytical"

    def test_g5_dominant(self):
        """G5 (dorsal parietal attention) dominant → analytical."""
        scores = _scores(g5=2.0, g3=1.0, g4=0.5)
        assert classify_completion(scores) == "analytical"

    def test_g8_dominant(self):
        """G8 (inferior parietal synthesis) dominant → analytical."""
        scores = _scores(g8=2.0, g7=1.5, g3=1.0)
        assert classify_completion(scores) == "analytical"

    def test_g1_g5_g8_all_in_top3(self):
        """All three cognitive groups in top 3 → analytical (no threat)."""
        scores = _scores(g1=1.5, g5=1.3, g8=1.1)
        assert classify_completion(scores) == "analytical"

    def test_non_marker_groups_default_to_analytical(self):
        """Top 3 = {G3, G6, G7} (language, motivation, memory) → analytical.

        These groups represent conceptual learning and default correctly.
        """
        scores = _scores(g3=2.0, g6=1.5, g7=1.0)
        assert classify_completion(scores) == "analytical"

    def test_g4_g10_g6_default_to_analytical(self):
        """Top 3 = {G4, G10, G6} (visual, reflective, motivation) → analytical."""
        scores = _scores(g4=1.8, g10=1.5, g6=1.2)
        assert classify_completion(scores) == "analytical"

    def test_all_zeros_returns_analytical(self):
        """No positive activations → analytical (default)."""
        scores = _scores()
        assert classify_completion(scores) == "analytical"

    def test_all_negative_returns_analytical(self):
        """All negative z-scores → no positive activations → analytical."""
        scores = {i: -0.5 for i in range(1, 11)}
        assert classify_completion(scores) == "analytical"


# =====================================================================
# Operational classification (G9 + G1/G5/G8 co-activation)
# =====================================================================

class TestOperational:
    """G9 (threat) + cognitive group co-activation in top 3 → operational."""

    def test_g9_plus_g1(self):
        """G9 + G1 co-activation → operational (decision under threat)."""
        scores = _scores(g9=2.0, g1=1.5, g3=0.5)
        assert classify_completion(scores) == "operational"

    def test_g9_plus_g5(self):
        """G9 + G5 co-activation → operational (SA under threat)."""
        scores = _scores(g9=1.8, g5=1.5, g4=0.8)
        assert classify_completion(scores) == "operational"

    def test_g9_plus_g8(self):
        """G9 + G8 co-activation → operational (pattern matching under threat)."""
        scores = _scores(g9=1.5, g8=1.8, g7=0.5)
        assert classify_completion(scores) == "operational"

    def test_g9_plus_g1_and_g8(self):
        """G9 + two cognitive groups → operational."""
        scores = _scores(g9=2.0, g1=1.8, g8=1.5)
        assert classify_completion(scores) == "operational"

    def test_operational_priority_over_procedural(self):
        """G9 + G1 + G2 all in top 3 → operational wins (checked first).

        Even though G2 is present, the co-activation pattern takes priority.
        """
        # G2 is pushed out of top 3 by G9, G1, G8
        scores = _scores(g9=2.0, g1=1.8, g8=1.5, g2=1.0)
        assert classify_completion(scores) == "operational"


# =====================================================================
# Critical edge cases
# =====================================================================

class TestEdgeCases:
    """Edge cases that validate the neuroscience reasoning."""

    def test_g2_g9_without_cognitive_is_procedural(self):
        """G2 + G9 without G1/G5/G8 → procedural, NOT operational.

        This is the Rasmussen SRK regression case: motor execution
        under threat without executive engagement. The operator is
        reacting physically without thinking — a failure mode.
        """
        scores = _scores(g2=2.0, g9=1.5, g3=0.8)
        assert classify_completion(scores) == "procedural"

    def test_g9_alone_without_cognitive_is_analytical(self):
        """G9 in top 3 but no cognitive groups → analytical (default).

        Threat without cognition is anxiety, not operational performance.
        """
        scores = _scores(g9=2.0, g3=1.5, g7=1.0)
        assert classify_completion(scores) == "analytical"

    def test_g9_with_g6_g7_no_cognitive_is_analytical(self):
        """G9 + G6 + G7 → analytical (G6 and G7 are not cognitive markers)."""
        scores = _scores(g9=2.0, g6=1.5, g7=1.0)
        assert classify_completion(scores) == "analytical"

    def test_g9_at_rank4_is_not_operational(self):
        """G9 just outside top 3 → NOT operational.

        A weakly activated G9 at rank #4 doesn't represent genuine
        threat engagement.
        """
        scores = _scores(g1=2.0, g5=1.8, g8=1.5, g9=1.0)
        # Top 3 = {G1, G5, G8}. G9 is 4th → no operational.
        assert classify_completion(scores) == "analytical"

    def test_partial_groups_dict(self):
        """Input with fewer than 10 groups still works."""
        scores = {2: 1.5, 3: 0.5}
        assert classify_completion(scores) == "procedural"

    def test_single_group(self):
        """Only one group has a positive z-score."""
        assert classify_completion({9: 1.0}) == "analytical"  # G9 alone, no cognitive
        assert classify_completion({2: 1.0}) == "procedural"
        assert classify_completion({1: 1.0}) == "analytical"

    def test_g2_g9_g1_all_high(self):
        """G2, G9, G1 all in top 3 → operational (G9+G1 co-activation wins).

        Operational is checked BEFORE procedural.
        """
        scores = _scores(g9=2.0, g1=1.8, g2=1.5)
        assert classify_completion(scores) == "operational"


# =====================================================================
# Points
# =====================================================================

class TestPoints:
    """Verify point values match Algorithm v3.2."""

    def test_procedural_points(self):
        assert POINTS_PROCEDURAL == 33

    def test_analytical_points(self):
        assert POINTS_ANALYTICAL == 33

    def test_operational_points(self):
        assert POINTS_OPERATIONAL == 34

    def test_total_equals_100(self):
        assert POINTS_PROCEDURAL + POINTS_ANALYTICAL + POINTS_OPERATIONAL == 100

    def test_completion_points_function(self):
        assert completion_points("procedural") == 33
        assert completion_points("analytical") == 33
        assert completion_points("operational") == 34

    def test_cognitive_groups_are_1_5_8(self):
        assert COGNITIVE_GROUPS == frozenset({1, 5, 8})

    def test_top_n_is_3(self):
        assert TOP_N == 3
