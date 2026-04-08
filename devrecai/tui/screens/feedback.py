"""
DevRecAI Feedback Screen.

Rating form for a past session outcome.
Collects per-dimension ratings (efficiency, adoption, stability)
and saves to DuckDB to improve the ML scorer.
"""
from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static, TextArea
from textual.containers import Horizontal, Vertical


class FeedbackScreen(Screen):
    """Session feedback rating form."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("ctrl+s", "submit", "Submit"),
    ]

    CSS = """
    FeedbackScreen {
        align: center middle;
        background: #0A0A0A;
    }

    #feedback-container {
        width: 70;
        height: auto;
        border: double #003B00;
        padding: 2 4;
    }

    #feedback-title {
        color: #00FF41;
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    .field-label {
        color: #00FF41;
        margin-top: 1;
    }

    Select {
        width: 100%;
        margin: 0 0 1 0;
    }

    TextArea {
        width: 100%;
        height: 4;
        margin: 0 0 1 0;
    }

    Input {
        width: 100%;
        margin: 0 0 1 0;
    }

    #btn-row {
        layout: horizontal;
        margin-top: 2;
        height: 3;
    }

    Button { width: 20; margin-right: 2; }

    #feedback-msg {
        color: #39FF14;
        margin-top: 1;
        text-align: center;
    }
    """

    RATING_OPTIONS = [
        ("1 — Poor", "1"),
        ("2 — Below average", "2"),
        ("3 — Average", "3"),
        ("4 — Good", "4"),
        ("5 — Excellent", "5"),
    ]

    def __init__(self, session_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._session_id = session_id

    def compose(self) -> ComposeResult:
        with Vertical(id="feedback-container"):
            yield Static(
                f"[ SESSION FEEDBACK ]\nSession: {self._session_id}",
                id="feedback-title",
            )
            yield Label("Tool Name (exact):", classes="field-label")
            yield Input(placeholder="e.g. GitHub Actions", id="tool-name")

            yield Label("Category:", classes="field-label")
            yield Input(placeholder="e.g. CI/CD", id="category")

            yield Label("Efficiency Outcome (1-5):", classes="field-label")
            yield Select(self.RATING_OPTIONS, value="3", id="outcome-efficiency")

            yield Label("Adoption Outcome (1-5):", classes="field-label")
            yield Select(self.RATING_OPTIONS, value="3", id="outcome-adoption")

            yield Label("Stability Outcome (1-5):", classes="field-label")
            yield Select(self.RATING_OPTIONS, value="3", id="outcome-stability")

            yield Label("Additional Notes (optional):", classes="field-label")
            yield TextArea(id="notes")

            with Horizontal(id="btn-row"):
                yield Button("Submit [Ctrl+S]", id="btn-submit", variant="success")
                yield Button("Cancel [Esc]", id="btn-cancel", variant="default")
            yield Static("", id="feedback-msg")

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_submit(self) -> None:
        asyncio.ensure_future(self._do_submit())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-submit":
            asyncio.ensure_future(self._do_submit())
        elif event.button.id == "btn-cancel":
            self.action_go_back()

    async def _do_submit(self) -> None:
        try:
            tool_name = self.query_one("#tool-name", Input).value.strip()
            category = self.query_one("#category", Input).value.strip()
            eff = int(str(self.query_one("#outcome-efficiency", Select).value))
            adp = int(str(self.query_one("#outcome-adoption", Select).value))
            stb = int(str(self.query_one("#outcome-stability", Select).value))
            notes = self.query_one("#notes", TextArea).text.strip()
            overall = round((eff + adp + stb) / 3.0, 2)

            if not tool_name:
                self.query_one("#feedback-msg", Static).update("✗ Tool name is required.")
                return

            from devrecai.storage.db import Database
            db = Database()
            await db.init()
            await db.save_feedback(
                session_id=self._session_id,
                tool_name=tool_name,
                category=category,
                outcome_efficiency=eff,
                outcome_adoption=adp,
                outcome_stability=stb,
                overall_score=overall,
                notes=notes,
            )
            self.query_one("#feedback-msg", Static).update(
                f"✓ Feedback saved! Overall score: {overall}/5.0"
            )
        except Exception as e:
            self.query_one("#feedback-msg", Static).update(f"✗ Error: {e}")
