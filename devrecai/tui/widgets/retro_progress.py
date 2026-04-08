"""
DevRecAI Retro Progress Bar Widget.

A custom Textual widget that renders an ASCII-art progress bar
in the retro green terminal style.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class RetroProgressBar(Widget):
    """ASCII-art progress bar widget with retro terminal styling."""

    DEFAULT_CSS = """
    RetroProgressBar {
        height: 3;
        width: 100%;
        content-align: center middle;
    }
    RetroProgressBar Static {
        text-align: center;
        color: $success;
    }
    """

    progress: reactive[int] = reactive(0)
    message: reactive[str] = reactive("Loading...")

    def __init__(
        self,
        bar_width: int = 50,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._bar_width = bar_width

    def compose(self) -> ComposeResult:
        yield Static(self._render_bar(), id="bar-content")

    def _render_bar(self) -> str:
        filled = int(self._bar_width * self.progress / 100)
        empty = self._bar_width - filled
        bar = "█" * filled + "░" * empty
        pct = f"{self.progress:3d}%"
        return f"[{bar}] {pct}  {self.message}"

    def watch_progress(self, value: int) -> None:
        """Update the bar display when progress changes."""
        self._refresh_bar()

    def watch_message(self, value: str) -> None:
        """Update the bar display when message changes."""
        self._refresh_bar()

    def _refresh_bar(self) -> None:
        try:
            bar = self.query_one("#bar-content", Static)
            bar.update(self._render_bar())
        except Exception:
            pass

    def set_progress(self, percent: int, message: str = "") -> None:
        """Set progress and optional status message."""
        self.progress = max(0, min(100, percent))
        if message:
            self.message = message
