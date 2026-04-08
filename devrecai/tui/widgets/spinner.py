"""
DevRecAI ASCII Spinner Widget.

Cycles through | / — \\ characters with status messages.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


SPINNER_FRAMES = ["|", "/", "—", "\\"]

LARGE_SPINNER_FRAMES = [
    "  ██  \n ████ \n  ██  ",
    "  ▀▀  \n ████ \n  ▄▄  ",
    "      \n ████ \n      ",
    "  ▄▄  \n ████ \n  ▀▀  ",
]


class SpinnerWidget(Widget):
    """Animated ASCII spinner with cycling status messages."""

    DEFAULT_CSS = """
    SpinnerWidget {
        height: 5;
        width: 100%;
        content-align: center middle;
    }
    SpinnerWidget Static {
        text-align: center;
        color: $success;
    }
    """

    tick: reactive[int] = reactive(0)
    status: reactive[str] = reactive("Processing...")

    def __init__(
        self,
        large: bool = False,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._large = large
        self._frames = LARGE_SPINNER_FRAMES if large else SPINNER_FRAMES

    def compose(self) -> ComposeResult:
        yield Static(self._current_frame(), id="spinner-content")

    def _current_frame(self) -> str:
        frame = self._frames[self.tick % len(self._frames)]
        return f"{frame}  {self.status}"

    def watch_tick(self, _: int) -> None:
        self._refresh_display()

    def watch_status(self, _: str) -> None:
        self._refresh_display()

    def _refresh_display(self) -> None:
        try:
            static = self.query_one("#spinner-content", Static)
            static.update(self._current_frame())
        except Exception:
            pass

    def advance(self, new_status: str | None = None) -> None:
        """Advance to the next spinner frame."""
        self.tick += 1
        if new_status is not None:
            self.status = new_status
