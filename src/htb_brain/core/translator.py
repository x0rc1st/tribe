"""Translator — maps region activations to the 10 capability groups with scores."""

import json
import logging
from pathlib import Path

import numpy as np

from htb_brain.core.atlas import RegionActivation

logger = logging.getLogger(__name__)


class GroupScore:
    __slots__ = ("id", "name", "score", "z_score", "rank", "engagement_pct",
                 "brain_area", "neuroscience", "offensive", "defensive",
                 "operator_frame", "region_scores")

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}


class Translator:
    """Maps region-level activations to 10 capability groups."""

    def __init__(self, cognitive_map_path: str | Path):
        self.cognitive_map_path = Path(cognitive_map_path)
        self.groups: list[dict] = []
        self._region_to_group: dict[str, int] = {}

    def load(self):
        with open(self.cognitive_map_path) as f:
            data = json.load(f)
        self.groups = data["groups"]
        self._region_to_group = {}
        for g in self.groups:
            for region in g["regions"]:
                self._region_to_group[region] = g["id"]
        logger.info("Loaded %d capability groups, %d region mappings",
                     len(self.groups), len(self._region_to_group))

    def translate(
        self,
        regions: dict[str, RegionActivation],
        region_zscores: dict[str, float],
    ) -> list[GroupScore]:
        """Compute group-level scores from region activations.

        Args:
            regions: region_name -> RegionActivation from atlas
            region_zscores: region_name -> z-score from aggregator

        Returns:
            List of GroupScore, sorted by score descending
        """
        group_scores = []

        for g in self.groups:
            member_zscores = []
            region_detail = {}
            for rname in g["regions"]:
                if rname in region_zscores:
                    member_zscores.append(region_zscores[rname])
                    region_detail[rname] = region_zscores[rname]

            score = float(np.mean(member_zscores)) if member_zscores else 0.0

            group_scores.append(GroupScore(
                id=g["id"],
                name=g["name"],
                score=score,
                z_score=score,
                rank=0,
                brain_area=g["brain_area"],
                neuroscience=g["neuroscience"],
                offensive=g["offensive"],
                defensive=g["defensive"],
                operator_frame=g["operator_frame"],
                region_scores=region_detail,
            ))

        # Rank by score
        group_scores.sort(key=lambda x: x.score, reverse=True)

        # Compute engagement percentage (0-100) from z-scores
        # Map: z <= 0 → 0%, max z → 100%
        max_z = max(gs.score for gs in group_scores) if group_scores else 1.0
        max_z = max(max_z, 0.01)  # avoid division by zero

        for i, gs in enumerate(group_scores):
            gs.rank = i + 1
            gs.engagement_pct = round(max(0.0, gs.score / max_z) * 100, 1)

        logger.info("Translated to %d groups. Top: %s (%.3f)",
                     len(group_scores), group_scores[0].name, group_scores[0].score)
        return group_scores

    def get_group_for_region(self, region_name: str) -> dict | None:
        gid = self._region_to_group.get(region_name)
        if gid is None:
            return None
        return next((g for g in self.groups if g["id"] == gid), None)
