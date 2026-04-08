"""
DevRecAI Root Textual Application.

Manages screen stack, global CSS theme, and app-level state.
"""
from __future__ import annotations

from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding

from devrecai.config.settings import get_settings

# ─── Retro Terminal CSS Theme ──────────────────────────────────────────────────

RETRO_GREEN_CSS = """
/* ═══════════════════════════════════════════ 
   DevRecAI Global Theme — Retro Green
   ═══════════════════════════════════════════ */

* {
    scrollbar-color: #00FF41;
    scrollbar-background: #0A0A0A;
}

Screen {
    background: #0A0A0A;
    color: #00FF41;
}

/* Borders & panels */
.panel {
    border: solid #003B00;
    background: #0D0D0D;
    padding: 1 2;
}

.panel-accent {
    border: double #00FF41;
    background: #0A0A0A;
    padding: 1 2;
}

/* Headers */
.section-header {
    color: #00FF41;
    text-style: bold;
    background: #003B00;
    padding: 0 2;
}

/* Status bar */
.status-bar {
    background: #003B00;
    color: #00FF41;
    height: 1;
    dock: bottom;
    padding: 0 2;
}

.status-bar-top {
    background: #003B00;
    color: #00FF41;
    height: 1;
    dock: top;
    padding: 0 2;
}

/* Buttons */
Button {
    background: #003B00;
    color: #00FF41;
    border: solid #00FF41;
    margin: 0 1;
}

Button:focus {
    background: #00FF41;
    color: #0A0A0A;
    border: solid #39FF14;
}

Button:hover {
    background: #005F00;
    color: #39FF14;
}

/* Inputs */
Input {
    background: #0D0D0D;
    color: #00FF41;
    border: solid #003B00;
}

Input:focus {
    border: solid #00FF41;
    background: #111111;
}

/* Select widget */
Select {
    background: #0D0D0D;
    color: #00FF41;
    border: solid #003B00;
}

/* DataTable */
DataTable {
    background: #0A0A0A;
    color: #00FF41;
}

DataTable > .datatable--header {
    background: #003B00;
    color: #39FF14;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #005F00;
    color: #39FF14;
}

DataTable > .datatable--hover {
    background: #001A00;
}

/* Tabs */
Tabs {
    background: #0A0A0A;
    border-bottom: solid #003B00;
}

Tab {
    color: #005F00;
}

Tab.-active {
    color: #00FF41;
    background: #003B00;
    text-style: bold;
}

/* TextArea / log */
TextArea {
    background: #0D0D0D;
    color: #00FF41;
    border: solid #003B00;
}

/* Labels */
Label {
    color: #00FF41;
}

.label-muted {
    color: #005F00;
}

.label-accent {
    color: #00CFFF;
}

.label-warning {
    color: #FFD700;
}

.label-error {
    color: #FF3131;
}

.label-highlight {
    color: #39FF14;
    text-style: bold;
}

/* Progress bar */
ProgressBar > .bar--bar {
    color: #00FF41;
}

ProgressBar > .bar--complete {
    color: #39FF14;
}

/* Logo area */
.logo-area {
    content-align: center middle;
    color: #00FF41;
    text-style: bold;
}

/* Menu items */
.menu-item {
    padding: 0 4;
    color: #005F00;
    height: 1;
}

.menu-item.--highlight,
.menu-item:focus {
    color: #00FF41;
    text-style: bold reverse;
}

/* Footer tip */
.footer-tip {
    color: #005F00;
    text-style: italic;
}

/* Comparison columns */
.compare-col {
    border: solid #003B00;
    padding: 0 1;
    width: 1fr;
}

/* Score colors */
.score-high { color: #39FF14; text-style: bold; }
.score-mid  { color: #FFD700; }
.score-low  { color: #FF3131; }
"""


class DevRecApp(App):
    """Root Textual application for DevRecAI."""

    TITLE = "DevRecAI — AI DevOps Tool Recommender"
    CSS = RETRO_GREEN_CSS

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(
        self,
        skip_boot: bool = False,
        start_screen: str = "boot",
        session_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._skip_boot = skip_boot
        self._start_screen = start_screen
        self._session_id = session_id
        self._settings = get_settings()
        self._profile: dict = {}
        self._results: dict = {}

    def on_mount(self) -> None:
        """Called when app mounts — push initial screen."""
        self._push_initial_screen()

    def _push_initial_screen(self) -> None:
        from devrecai.tui.screens.boot import BootScreen
        from devrecai.tui.screens.home import HomeScreen
        from devrecai.tui.screens.history import HistoryScreen
        from devrecai.tui.screens.config_screen import ConfigScreen
        from devrecai.tui.screens.feedback import FeedbackScreen

        if self._start_screen == "history":
            self.push_screen(HistoryScreen())
        elif self._start_screen == "config":
            self.push_screen(ConfigScreen())
        elif self._start_screen == "feedback" and self._session_id:
            self.push_screen(FeedbackScreen(session_id=self._session_id))
        elif self._skip_boot or self._settings.theme.boot_sequence is False:
            self.push_screen(HomeScreen())
        else:
            self.push_screen(BootScreen())

    def goto_home(self) -> None:
        """Navigate to the home screen (replaces current screen)."""
        from devrecai.tui.screens.home import HomeScreen
        self.switch_screen(HomeScreen())

    def goto_wizard(self) -> None:
        """Navigate to the input wizard."""
        from devrecai.tui.screens.input_wizard import InputWizardScreen
        self.push_screen(InputWizardScreen())

    def switch_screen_with_processing(self, profile: dict) -> None:
        """Switch directly to ProcessingScreen, replacing the wizard."""
        from devrecai.tui.screens.processing import ProcessingScreen
        self._profile = profile
        self.switch_screen(ProcessingScreen(profile=profile))

    def goto_processing(self, profile: dict) -> None:
        """Navigate to the processing screen (push onto stack)."""
        from devrecai.tui.screens.processing import ProcessingScreen
        self._profile = profile
        self.switch_screen(ProcessingScreen(profile=profile))

    def goto_results(self, profile: dict, results: dict) -> None:
        """Navigate to results screen with scoring data."""
        from devrecai.tui.screens.results import ResultsScreen
        self._profile = profile
        self._results = results
        self.switch_screen(ResultsScreen(profile=profile, results=results))

    def goto_history(self) -> None:
        """Navigate to history screen."""
        from devrecai.tui.screens.history import HistoryScreen
        self.push_screen(HistoryScreen())

    def goto_config(self) -> None:
        """Navigate to config screen."""
        from devrecai.tui.screens.config_screen import ConfigScreen
        self.push_screen(ConfigScreen())
