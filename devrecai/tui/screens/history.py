"""
DevRecAI History Screen.

Scrollable list of all past recommendation sessions.
Columns: Session ID | Project Name | Date | Top Tool | Status
Actions: Enter=view, D=delete, E=re-export
"""
from __future__ import annotations

import asyncio
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Label, Static
from textual.containers import Vertical

from rich.text import Text


class HistoryScreen(Screen):
    """Session history browser."""

    BINDINGS = [
        Binding("enter", "view_session", "View"),
        Binding("d", "delete_session", "Delete"),
        Binding("e", "export_session", "Re-export"),
        Binding("escape", "go_back", "Back"),
        Binding("q", "go_back", "Back"),
    ]

    CSS = """
    HistoryScreen {
        background: #0A0A0A;
        align: center top;
        padding: 1;
    }

    #history-header {
        background: #003B00;
        color: #00FF41;
        text-style: bold;
        height: 1;
        dock: top;
        padding: 0 2;
        width: 100%;
    }

    #history-container {
        width: 100%;
        height: 1fr;
        padding: 0 2;
    }

    #title-bar {
        color: #00CFFF;
        text-style: bold;
        margin: 1 0;
    }

    DataTable {
        height: 1fr;
    }

    #action-bar {
        background: #001A00;
        color: #005F00;
        height: 1;
        dock: bottom;
        padding: 0 2;
    }

    #empty-label {
        color: #005F00;
        text-align: center;
        padding: 4;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._sessions: list[dict] = []
        self._selected_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Static(
            " SESSION HISTORY — DevRecAI",
            id="history-header",
        )
        with Vertical(id="history-container"):
            yield Label("Recent Sessions:", id="title-bar")
            yield DataTable(id="session-table", cursor_type="row")
            yield Label("No sessions yet. Run [devrec run] to get started.", id="empty-label")
        yield Static(
            " [Enter] View  [E] Re-export  [D] Delete  [Q] Back",
            id="action-bar",
        )

    def on_mount(self) -> None:
        table = self.query_one("#session-table", DataTable)
        table.add_columns("Session ID", "Project Name", "Date", "Top Tool", "Status")
        self.call_after_refresh(self._load_sessions)

    async def _load_sessions(self) -> None:
        try:
            from devrecai.storage.sessions import SessionManager
            sm = SessionManager()
            self._sessions = await sm.list_sessions()
            self._populate_table()
        except Exception as e:
            self.query_one("#empty-label", Label).update(f"Error loading sessions: {e}")

    def _populate_table(self) -> None:
        table = self.query_one("#session-table", DataTable)
        table.clear()

        if not self._sessions:
            self.query_one("#empty-label", Label).display = True
            return

        self.query_one("#empty-label", Label).display = False
        for sess in self._sessions:
            sid = sess.get("session_id", "")[:8] + "..."
            name = sess.get("project_name", "Unnamed")
            date = str(sess.get("created_at", ""))[:10]
            top_tool = sess.get("top_tool", "N/A")
            status = sess.get("status", "complete")

            status_color = "green" if status == "complete" else "yellow"
            table.add_row(
                Text(sid, style="dim cyan"),
                Text(name, style="bold white"),
                Text(date, style="dim"),
                Text(top_tool, style="bright_green"),
                Text(status, style=status_color),
                key=sess.get("session_id"),
            )

    def on_data_table_row_selected(self, event) -> None:
        self._selected_id = str(event.row_key.value) if event.row_key else None

    def action_view_session(self) -> None:
        if not self._selected_id:
            return
        sess = next((s for s in self._sessions if s.get("session_id") == self._selected_id), None)
        if sess:
            from devrecai.tui.screens.results import ResultsScreen
            self.app.push_screen(
                ResultsScreen(
                    profile=sess.get("profile_json", {}),
                    results=sess.get("results_json", {}),
                )
            )

    def action_delete_session(self) -> None:
        if not self._selected_id:
            return
        asyncio.ensure_future(self._do_delete())

    async def _do_delete(self) -> None:
        try:
            from devrecai.storage.sessions import SessionManager
            sm = SessionManager()
            await sm.delete_session(self._selected_id)
            await self._load_sessions()
        except Exception:
            pass

    def action_export_session(self) -> None:
        if not self._selected_id:
            return
        sess = next((s for s in self._sessions if s.get("session_id") == self._selected_id), None)
        if sess:
            from devrecai.tui.screens.export_screen import ExportScreen
            self.app.push_screen(
                ExportScreen(
                    profile=sess.get("profile_json", {}),
                    results=sess.get("results_json", {}),
                )
            )

    def action_go_back(self) -> None:
        self.app.pop_screen()
