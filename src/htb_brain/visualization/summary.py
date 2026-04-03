"""Human-readable narrative summary generation."""

import logging

from htb_brain.core.translator import GroupScore

logger = logging.getLogger(__name__)

CAVEAT = (
    "> **Note**: These predictions are population-averaged and reflect how content like this "
    "typically engages cognitive regions during *perception*, not individual learning outcomes. "
    "Think of this as a cognitive fingerprint of the content itself."
)


def generate_summary(
    group_scores: list[GroupScore],
    top_n: int = 5,
    content_type: str = "content",
) -> str:
    """Generate a markdown narrative summary of engagement.

    Args:
        group_scores: sorted list of GroupScore from Translator
        top_n: number of top groups to highlight
        content_type: "text", "video", "lab recording" for framing

    Returns:
        Markdown string
    """
    top = group_scores[:top_n]
    bottom = group_scores[-2:]

    lines = [f"## Brain Engagement Report\n"]
    lines.append(f"This {content_type} primarily engages **{top[0].name}** "
                 f"(rank #1, z={top[0].score:.2f}), driven by the "
                 f"{top[0].brain_area}.\n")

    # Top engaged
    lines.append("### Most Engaged Capabilities\n")
    for gs in top:
        lines.append(f"**{gs.rank}. {gs.name}** (z={gs.score:.2f})")
        lines.append(f"- *{gs.operator_frame}*")
        lines.append(f"- **Offensive relevance**: {gs.offensive}")
        lines.append(f"- **Defensive relevance**: {gs.defensive}")
        lines.append("")

    # Insight
    lines.append("### Key Insight\n")
    if top[0].score > 1.0:
        lines.append(
            f"This content strongly activates **{top[0].name}** circuits, "
            f"suggesting it demands significant {_simplify_neuro(top[0].neuroscience)}. "
        )
    else:
        lines.append(
            f"This content shows moderate, distributed engagement across multiple "
            f"cognitive systems, with a slight emphasis on **{top[0].name}**. "
        )

    if len(top) >= 3:
        names = [t.name for t in top[1:3]]
        lines.append(
            f"It also engages **{names[0]}** and **{names[1]}**, "
            f"indicating multi-faceted cognitive demand.\n"
        )

    # Least engaged
    lines.append("### Least Engaged\n")
    for gs in bottom:
        lines.append(f"- {gs.name} (z={gs.score:.2f})")
    lines.append("")

    # Caveat
    lines.append("---\n")
    lines.append(CAVEAT)

    return "\n".join(lines)


def _simplify_neuro(neuro: str) -> str:
    """Extract first 2-3 key terms from neuroscience description."""
    terms = [t.strip() for t in neuro.split(",")]
    return ", ".join(terms[:3]).lower()
