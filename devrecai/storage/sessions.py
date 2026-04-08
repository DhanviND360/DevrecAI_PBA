"""
DevRecAI Session Manager.

High-level session save/resume/list/delete logic built on top of db.py.
"""
from __future__ import annotations

from typing import Optional

from devrecai.storage.db import Database


class SessionManager:
    """High-level session persistence manager."""

    def __init__(self) -> None:
        self._db = Database()

    async def _ensure_init(self) -> None:
        await self._db.init()

    async def save(
        self,
        project_name: str,
        profile: dict,
        results: dict,
        report_path: str = "",
    ) -> str:
        """Save a completed recommendation session. Returns session_id."""
        await self._ensure_init()
        return await self._db.save_session(
            project_name=project_name,
            profile=profile,
            results=results,
            report_path=report_path,
        )

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve full session data by ID."""
        await self._ensure_init()
        return await self._db.get_session(session_id)

    async def list_sessions(self, limit: int = 50) -> list[dict]:
        """Return list of sessions sorted newest first."""
        await self._ensure_init()
        return await self._db.list_sessions(limit=limit)

    async def delete_session(self, session_id: str) -> None:
        """Permanently delete a session from history."""
        await self._ensure_init()
        await self._db.delete_session(session_id)

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
        """Save user feedback for a session's tool outcome."""
        await self._ensure_init()
        return await self._db.save_feedback(
            session_id=session_id,
            tool_name=tool_name,
            category=category,
            outcome_efficiency=outcome_efficiency,
            outcome_adoption=outcome_adoption,
            outcome_stability=outcome_stability,
            overall_score=overall_score,
            notes=notes,
        )
