"""SQLite-backed storage for Algorithm v3.2 skill mastery.

Stores completion records and computes skill mastery + ORI on read.
Thread-safe via thread-local connections (same pattern as profile_store.py).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from htb_brain.core.completion_classifier import classify_completion
from htb_brain.core.skill_mastery import (
    Certification,
    Completion,
    calculate_skill_mastery,
)
from htb_brain.core.ori import calculate_ori

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path("/workspace/tribe/data/mastery.db")


class MasteryStore:
    """Thread-safe SQLite store for skill mastery tracking."""

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = str(db_path or _DEFAULT_DB)
        self._local = threading.local()
        self._ensure_schema()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _ensure_schema(self):
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operator_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                completion_type TEXT NOT NULL,
                skill_tags TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                group_z_scores TEXT NOT NULL DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_completions_operator
                ON completions(operator_id);

            CREATE TABLE IF NOT EXISTS certifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operator_id TEXT NOT NULL,
                cert_id TEXT NOT NULL,
                skill_tags TEXT NOT NULL,
                earned_at TEXT NOT NULL,
                UNIQUE(operator_id, cert_id)
            );

            CREATE INDEX IF NOT EXISTS idx_certs_operator
                ON certifications(operator_id);

            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS role_skills (
                role_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                UNIQUE(role_id, skill_id)
            );

            CREATE TABLE IF NOT EXISTS role_certs (
                role_id TEXT NOT NULL,
                cert_id TEXT NOT NULL,
                UNIQUE(role_id, cert_id)
            );
        """)
        conn.commit()

    # ------------------------------------------------------------------
    # Skills / Roles setup
    # ------------------------------------------------------------------

    def upsert_skill(self, skill_id: str, name: str = "") -> None:
        conn = self._conn()
        conn.execute(
            "INSERT INTO skills (skill_id, name) VALUES (?, ?) "
            "ON CONFLICT(skill_id) DO UPDATE SET name = excluded.name",
            (skill_id, name),
        )
        conn.commit()

    def add_role_skill(self, role_id: str, skill_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "INSERT OR IGNORE INTO role_skills (role_id, skill_id) VALUES (?, ?)",
            (role_id, skill_id),
        )
        conn.commit()

    def add_role_cert(self, role_id: str, cert_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "INSERT OR IGNORE INTO role_certs (role_id, cert_id) VALUES (?, ?)",
            (role_id, cert_id),
        )
        conn.commit()

    # ------------------------------------------------------------------
    # Record completions
    # ------------------------------------------------------------------

    def record_completion(
        self,
        operator_id: str,
        course_id: str,
        completion_type: str,
        skill_tags: list[str],
        group_z_scores: dict[int, float] | None = None,
        completed_at: datetime | None = None,
    ) -> dict:
        conn = self._conn()
        now = (completed_at or datetime.now(timezone.utc)).isoformat()
        gz = json.dumps({str(k): v for k, v in (group_z_scores or {}).items()})

        conn.execute(
            """INSERT INTO completions
               (operator_id, course_id, completion_type, skill_tags, completed_at, group_z_scores)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (operator_id, course_id, completion_type, json.dumps(skill_tags), now, gz),
        )
        conn.commit()

        # Auto-register skills
        for sid in skill_tags:
            self.upsert_skill(sid)

        return {
            "operator_id": operator_id,
            "course_id": course_id,
            "completion_type": completion_type,
            "skill_tags": skill_tags,
            "completed_at": now,
        }

    def record_certification(
        self,
        operator_id: str,
        cert_id: str,
        skill_tags: list[str],
        earned_at: datetime | None = None,
    ) -> dict:
        conn = self._conn()
        now = (earned_at or datetime.now(timezone.utc)).isoformat()
        conn.execute(
            """INSERT INTO certifications (operator_id, cert_id, skill_tags, earned_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(operator_id, cert_id) DO UPDATE SET
                 skill_tags = excluded.skill_tags, earned_at = excluded.earned_at""",
            (operator_id, cert_id, json.dumps(skill_tags), now),
        )
        conn.commit()
        return {"operator_id": operator_id, "cert_id": cert_id, "earned_at": now}

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def _load_completions(self, operator_id: str) -> list[Completion]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM completions WHERE operator_id = ? ORDER BY completed_at",
            (operator_id,),
        ).fetchall()
        result = []
        for r in rows:
            result.append(Completion(
                course_id=r["course_id"],
                completion_type=r["completion_type"],
                skill_tags=json.loads(r["skill_tags"]),
                date=datetime.fromisoformat(r["completed_at"]),
            ))
        return result

    def _load_certifications(self, operator_id: str) -> list[Certification]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM certifications WHERE operator_id = ? ORDER BY earned_at",
            (operator_id,),
        ).fetchall()
        result = []
        for r in rows:
            result.append(Certification(
                cert_id=r["cert_id"],
                skill_tags=json.loads(r["skill_tags"]),
                date=datetime.fromisoformat(r["earned_at"]),
            ))
        return result

    def _get_skill_ids(self, operator_id: str) -> list[str]:
        """Get all skill IDs this operator has touched."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT DISTINCT skill_id FROM skills ORDER BY skill_id"
        ).fetchall()
        return [r["skill_id"] for r in rows]

    def get_skills(self, operator_id: str, as_of_date: datetime | None = None) -> dict:
        completions = self._load_completions(operator_id)
        certifications = self._load_certifications(operator_id)
        skill_ids = self._get_skill_ids(operator_id)

        if not skill_ids:
            return {"operator_id": operator_id, "skills": [], "total_skills": 0}

        skills = []
        for sid in skill_ids:
            sm = calculate_skill_mastery(sid, completions, certifications, as_of_date)
            if sm.peak > 0 or True:  # show all known skills
                skills.append({
                    "skill_id": sm.skill_id,
                    "peak": sm.peak,
                    "current": sm.current,
                    "stage": sm.stage,
                    "health": sm.health,
                    "completed_types": sorted(sm.completed_types),
                    "total_completions": sm.total_completions,
                    "completions_by_type": sm.completions_by_type,
                    "last_activity": sm.last_activity.isoformat() if sm.last_activity else None,
                })

        return {
            "operator_id": operator_id,
            "skills": skills,
            "total_skills": len(skills),
        }

    def get_ori(
        self,
        operator_id: str,
        role_id: str | None = None,
        as_of_date: datetime | None = None,
    ) -> dict:
        completions = self._load_completions(operator_id)
        certifications = self._load_certifications(operator_id)
        cert_objects = self._load_certifications(operator_id)

        # Determine required skills
        conn = self._conn()
        if role_id:
            rows = conn.execute(
                "SELECT skill_id FROM role_skills WHERE role_id = ?", (role_id,)
            ).fetchall()
            skill_ids = [r["skill_id"] for r in rows]
            cert_rows = conn.execute(
                "SELECT cert_id FROM role_certs WHERE role_id = ?", (role_id,)
            ).fetchall()
            required_certs = [r["cert_id"] for r in cert_rows]
        else:
            # Use all skills the operator has touched
            skill_ids = self._get_skill_ids(operator_id)
            required_certs = []

        if not skill_ids:
            return calculate_ori([], [], set())

        # Compute mastery for each skill
        from htb_brain.core.skill_mastery import SkillMastery
        masteries = []
        for sid in skill_ids:
            sm = calculate_skill_mastery(sid, completions, certifications, as_of_date)
            masteries.append(sm)

        held_certs = {c.cert_id for c in cert_objects}

        result = calculate_ori(masteries, required_certs, held_certs)
        result["operator_id"] = operator_id
        result["role_id"] = role_id
        return result

    def get_completions(self, operator_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM completions WHERE operator_id = ? ORDER BY completed_at DESC",
            (operator_id,),
        ).fetchall()
        return [
            {
                "course_id": r["course_id"],
                "completion_type": r["completion_type"],
                "skill_tags": json.loads(r["skill_tags"]),
                "completed_at": r["completed_at"],
            }
            for r in rows
        ]

    def delete_operator(self, operator_id: str) -> int:
        conn = self._conn()
        c1 = conn.execute(
            "DELETE FROM completions WHERE operator_id = ?", (operator_id,)
        )
        c2 = conn.execute(
            "DELETE FROM certifications WHERE operator_id = ?", (operator_id,)
        )
        conn.commit()
        return c1.rowcount + c2.rowcount
