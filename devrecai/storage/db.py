"""
DevRecAI DuckDB Interface.

Creates and manages sessions, feedback, and training_log tables.
Provides CRUD operations for session persistence and feedback collection.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from devrecai.config.settings import DEVREC_DIR

logger = logging.getLogger(__name__)

DB_PATH = DEVREC_DIR / "sessions.db"


class Database:
    """Async-compatible DuckDB interface."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = str(db_path or DB_PATH)
        self._conn = None

    def _connect(self):
        """Get or create a DuckDB connection."""
        if self._conn is None:
            import duckdb
            DEVREC_DIR.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(self._db_path)
        return self._conn

    async def init(self) -> None:
        """Create tables if they don't exist."""
        conn = self._connect()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id  VARCHAR PRIMARY KEY,
                created_at  TIMESTAMP,
                project_name VARCHAR,
                profile_json JSON,
                results_json JSON,
                report_path  VARCHAR,
                status       VARCHAR DEFAULT 'complete'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id        VARCHAR PRIMARY KEY,
                session_id         VARCHAR,
                tool_name          VARCHAR,
                category           VARCHAR,
                outcome_efficiency INTEGER,
                outcome_adoption   INTEGER,
                outcome_stability  INTEGER,
                overall_score      DOUBLE,
                notes              VARCHAR,
                submitted_at       TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS training_log (
                run_id              VARCHAR PRIMARY KEY,
                run_at              TIMESTAMP,
                sample_count        INTEGER,
                rmse                DOUBLE,
                model_path          VARCHAR,
                feature_importances JSON
            )
        """)

    # ─── Sessions ─────────────────────────────────────────────────────────────

    async def save_session(
        self,
        project_name: str,
        profile: dict,
        results: dict,
        report_path: str = "",
        status: str = "complete",
    ) -> str:
        """Insert a new session record. Returns session_id."""
        session_id = str(uuid.uuid4())
        conn = self._connect()
        conn.execute(
            """
            INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                session_id,
                datetime.now(),
                project_name,
                json.dumps(profile),
                json.dumps(results),
                report_path,
                status,
            ],
        )
        return session_id

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve a session by ID."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", [session_id]
        ).fetchall()
        if not rows:
            return None
        cols = ["session_id", "created_at", "project_name", "profile_json", "results_json", "report_path", "status"]
        row = rows[0]
        result = dict(zip(cols, row))
        result["profile_json"] = json.loads(result["profile_json"]) if result["profile_json"] else {}
        result["results_json"] = json.loads(result["results_json"]) if result["results_json"] else {}
        return result

    async def list_sessions(self, limit: int = 50) -> list[dict]:
        """List all sessions sorted by created_at descending."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT session_id, created_at, project_name, status FROM sessions "
            "ORDER BY created_at DESC LIMIT ?",
            [limit],
        ).fetchall()
        sessions = []
        for row in rows:
            sessions.append({
                "session_id": row[0],
                "created_at": str(row[1]),
                "project_name": row[2],
                "status": row[3],
                "top_tool": "N/A",  # Would need results lookup
            })
        return sessions

    async def delete_session(self, session_id: str) -> None:
        """Delete a session by ID."""
        conn = self._connect()
        conn.execute("DELETE FROM sessions WHERE session_id = ?", [session_id])

    # ─── Feedback ─────────────────────────────────────────────────────────────

    async def save_feedback(
        self,
        session_id: str,
        tool_name: str,
        category: str,
        outcome_efficiency: int,
        outcome_adoption: int,
        outcome_stability: int,
        overall_score: float,
        notes: str = "",
    ) -> str:
        """Insert a feedback record. Returns feedback_id."""
        feedback_id = str(uuid.uuid4())
        conn = self._connect()
        conn.execute(
            "INSERT INTO feedback VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                feedback_id, session_id, tool_name, category,
                outcome_efficiency, outcome_adoption, outcome_stability,
                overall_score, notes, datetime.now(),
            ],
        )
        return feedback_id

    async def count_feedback(self) -> int:
        """Return total number of feedback rows."""
        conn = self._connect()
        result = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()
        return int(result[0]) if result else 0

    async def get_feedback_for_training(self) -> list[dict]:
        """
        Return feedback rows joined with session profile data
        for use in ML training.
        """
        conn = self._connect()
        rows = conn.execute("""
            SELECT
                f.tool_name, f.category,
                f.outcome_efficiency, f.outcome_adoption, f.outcome_stability,
                f.overall_score, f.notes,
                s.profile_json
            FROM feedback f
            JOIN sessions s ON f.session_id = s.session_id
        """).fetchall()

        result = []
        for row in rows:
            profile = json.loads(row[7]) if row[7] else {}
            result.append({
                "tool_name": row[0],
                "category": row[1],
                "outcome_efficiency": row[2],
                "outcome_adoption": row[3],
                "outcome_stability": row[4],
                "overall_score": row[5],
                "notes": row[6],
                **profile,
            })
        return result

    # ─── Training Log ─────────────────────────────────────────────────────────

    async def save_training_log(
        self,
        sample_count: int,
        rmse: float,
        model_path: str,
        feature_importances: dict,
    ) -> str:
        """Insert a training run log record."""
        run_id = str(uuid.uuid4())
        conn = self._connect()
        conn.execute(
            "INSERT INTO training_log VALUES (?, ?, ?, ?, ?, ?)",
            [run_id, datetime.now(), sample_count, rmse, model_path, json.dumps(feature_importances)],
        )
        return run_id

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
