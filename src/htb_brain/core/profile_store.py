"""SQLite-backed storage for Operator Readiness Profiles.

Stores module engagement records and computes accumulated dimension
profiles per operator. Uses stdlib sqlite3 — no extra dependencies.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from htb_brain.core.operator_readiness import compute_readiness, readiness_level

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path("/workspace/tribe/data/operator_profiles.db")

# Dimension keys in canonical order
DIMENSION_KEYS = [
    "procedural_automaticity",
    "threat_detection",
    "situational_awareness",
    "strategic_decision",
    "analytical_synthesis",
    "stress_resilience",
]


class ProfileStore:
    """Thread-safe SQLite store for operator readiness profiles."""

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = str(db_path or _DEFAULT_DB)
        self._local = threading.local()
        # Initialize schema on first connection
        self._ensure_schema()

    def _conn(self) -> sqlite3.Connection:
        """Get a thread-local connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _ensure_schema(self):
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS module_engagements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operator_id TEXT NOT NULL,
                module_id TEXT NOT NULL,
                module_name TEXT NOT NULL DEFAULT '',
                predicted_at TEXT NOT NULL,
                group_scores TEXT NOT NULL,       -- JSON {group_id: z_score}
                subcortical_scores TEXT NOT NULL,  -- JSON {structure: {z_score, engaged}}
                dimensions TEXT NOT NULL,          -- JSON {dim_key: {covered, strength, ...}}
                UNIQUE(operator_id, module_id)
            );

            CREATE INDEX IF NOT EXISTS idx_engagements_operator
                ON module_engagements(operator_id);
        """)
        conn.commit()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record_module(
        self,
        operator_id: str,
        module_id: str,
        module_name: str,
        group_scores: dict[int, float],
        subcortical_scores: dict[str, dict],
        dimensions: dict[str, dict],
    ) -> dict:
        """Record a module's dimension scores for an operator.

        If the same (operator_id, module_id) already exists, it is replaced.
        """
        conn = self._conn()
        now = datetime.now(timezone.utc).isoformat()

        # Convert int keys to str for JSON
        gs_json = json.dumps({str(k): v for k, v in group_scores.items()})
        sc_json = json.dumps(subcortical_scores)
        dim_json = json.dumps(dimensions)

        conn.execute(
            """INSERT INTO module_engagements
               (operator_id, module_id, module_name, predicted_at,
                group_scores, subcortical_scores, dimensions)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(operator_id, module_id) DO UPDATE SET
                 module_name = excluded.module_name,
                 predicted_at = excluded.predicted_at,
                 group_scores = excluded.group_scores,
                 subcortical_scores = excluded.subcortical_scores,
                 dimensions = excluded.dimensions
            """,
            (operator_id, module_id, module_name, now, gs_json, sc_json, dim_json),
        )
        conn.commit()

        return {
            "operator_id": operator_id,
            "module_id": module_id,
            "module_name": module_name,
            "predicted_at": now,
            "dimensions": dimensions,
        }

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_profile(self, operator_id: str) -> dict:
        """Compute the accumulated readiness profile for an operator.

        Returns the OperatorProfile data model from Section 7 of the design doc.
        """
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM module_engagements WHERE operator_id = ? ORDER BY predicted_at",
            (operator_id,),
        ).fetchall()

        # Build completed_modules list and accumulate per-dimension strengths
        completed_modules: list[dict] = []
        dim_strengths: dict[str, list[float]] = {k: [] for k in DIMENSION_KEYS}

        for row in rows:
            dims = json.loads(row["dimensions"])
            module = {
                "module_id": row["module_id"],
                "module_name": row["module_name"],
                "predicted_at": row["predicted_at"],
                "group_scores": json.loads(row["group_scores"]),
                "subcortical_scores": json.loads(row["subcortical_scores"]),
                "dimensions": dims,
            }
            completed_modules.append(module)

            for dim_key in DIMENSION_KEYS:
                dim_data = dims.get(dim_key, {})
                dim_strengths[dim_key].append(dim_data.get("strength", 0.0))

        total_modules = len(completed_modules)

        # Build dimension scores using accumulated readiness
        dimension_scores: dict[str, dict] = {}
        for dim_key in DIMENSION_KEYS:
            strengths = dim_strengths[dim_key]
            rdns = compute_readiness(strengths) if strengths else 0.0
            raw_signal = sum(max(0.0, s) for s in strengths)
            dimension_scores[dim_key] = {
                "readiness": round(rdns, 3),
                "level": readiness_level(rdns),
                "raw_signal": round(raw_signal, 3),
                "mean_strength": round(
                    sum(strengths) / len(strengths), 3
                ) if strengths else 0.0,
                "module_contributions": len([s for s in strengths if s > 0]),
            }

        return {
            "operator_id": operator_id,
            "dimensions": dimension_scores,
            "completed_modules": completed_modules,
            "total_modules": total_modules,
        }

    def get_dimension_readiness(self, operator_id: str) -> dict[str, float]:
        """Get just the readiness values for gap detection."""
        profile = self.get_profile(operator_id)
        return {
            dim_key: dim_data["readiness"]
            for dim_key, dim_data in profile["dimensions"].items()
        }

    def delete_operator(self, operator_id: str) -> int:
        """Delete all records for an operator. Returns rows deleted."""
        conn = self._conn()
        cursor = conn.execute(
            "DELETE FROM module_engagements WHERE operator_id = ?",
            (operator_id,),
        )
        conn.commit()
        return cursor.rowcount
