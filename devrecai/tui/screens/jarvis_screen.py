"""
DevRecAI JARVIS Intro Screen.

Displayed between the Home screen and the Input Wizard when the user
selects [1] New Session.  Shows a cyberpunk/JARVIS-style radial animation
for ~3.5 seconds, then automatically advances to the Input Wizard.
Any key press skips immediately.
"""
from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static

from devrecai.tui.animations.jarvis_animation import _build_frame, _colorize


class JarvisScreen(Screen):
    """Full-screen JARVIS/cyberpunk radial animation screen."""

    # No BINDINGS shown in the footer — it's a pure animation
    BINDINGS = [
        Binding("space",  "skip", "Skip", show=False),
        Binding("enter",  "skip", "Skip", show=False),
        Binding("escape", "skip", "Skip", show=False),
    ]

    CSS = """
    JarvisScreen {
        background: #00060A;
        align: center middle;
        padding: 0;
    }

    #jarvis-canvas {
        width: 78;
        height: 24;
        background: #00060A;
        color: cyan;
        text-align: left;
        content-align: center middle;
    }

    #jarvis-outer {
        align: center middle;
        width: 100%;
        height: 100%;
        border: double #003344;
        background: #00060A;
    }
    """

    # Total ticks before auto-advance (tick = 60 ms  →  ~3.6 s)
    _MAX_TICKS: int = 60

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tick = 0
        self._done = False

    def compose(self) -> ComposeResult:
        with Static(id="jarvis-outer"):
            yield Static("", id="jarvis-canvas", markup=True)

    def on_mount(self) -> None:
        # First frame immediately, then update every 60 ms
        self._render_frame()
        self.set_interval(0.06, self._step)

    def _step(self) -> None:
        if self._done:
            return
        self._tick += 1
        self._render_frame()
        if self._tick >= self._MAX_TICKS:
            self._done = True
            self._go_wizard()

    def _render_frame(self) -> None:
        frame = _build_frame(self._tick)
        colored = _colorize(frame, self._tick)
        try:
            self.query_one("#jarvis-canvas", Static).update(colored)
        except Exception:
            pass

    # ── Key handling ──────────────────────────────────────────────────────

    def action_skip(self) -> None:
        self._done = True
        self._go_wizard()

    def on_key(self, event) -> None:
        self._done = True
        self._go_wizard()

    # ── Navigation ────────────────────────────────────────────────────────

    def _go_wizard(self) -> None:
        from devrecai.tui.screens.input_wizard import InputWizardScreen
        self.app.switch_screen(InputWizardScreen())
