"""
DevRecAI Boot Screen.

Full terminal takeover with retro BIOS boot animation:
- ASCII art DevRecAI logo with scanline shimmer
- Fake BIOS POST lines
- Animated progress bar
- Version string
- Press any key to skip
"""
from __future__ import annotations

import asyncio
from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Label, Static, Footer

from devrecai.tui.animations.boot_animation import (
    BOOT_LOGO,
    PROGRESS_MESSAGES,
    build_progress_bar,
    get_spinner_frame,
    get_post_lines,
)


class BootScreen(Screen):
    """Retro BIOS boot animation screen."""

    BINDINGS = [
        Binding("space", "skip", "Skip", show=False),
        Binding("enter", "skip", "Skip", show=False),
        Binding("escape", "skip", "Skip", show=False),
    ]

    CSS = """
    BootScreen {
        align: center middle;
        background: #0A0A0A;
    }

    #boot-container {
        width: 80;
        height: auto;
        align: center top;
        padding: 1 2;
    }

    #logo-display {
        color: #00FF41;
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    #post-lines {
        color: #005F00;
        width: 100%;
        height: 18;
        overflow: hidden;
    }

    #progress-area {
        color: #00FF41;
        width: 100%;
        margin-top: 1;
        text-align: center;
    }

    #version-line {
        color: #003B00;
        text-align: right;
        width: 100%;
        margin-top: 1;
    }

    #press-key {
        color: #39FF14;
        text-style: bold blink;
        text-align: center;
        margin-top: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._post_idx = 0
        self._progress = 0
        self._tick = 0
        self._done = False
        self._skipped = False
        # Load real system specs once (cached after first call)
        self._post_lines: list[str] = []

    def compose(self) -> ComposeResult:
        import sys, platform
        py_ver = sys.version.split()[0]
        os_info = platform.system() + " " + platform.release()
        with Static(id="boot-container"):
            yield Static(BOOT_LOGO, id="logo-display")
            yield Static("", id="post-lines")
            yield Static("", id="progress-area")
            yield Static(
                f"DevRecAI v1.0.0  │  Python {py_ver}  │  {os_info}  │  {datetime.now().strftime('%Y-%m-%d')}",
                id="version-line",
            )
            yield Static("[ PRESS ANY KEY TO CONTINUE ]", id="press-key")

    def on_mount(self) -> None:
        """Collect live system specs then start the boot animation timer."""
        self._post_lines = get_post_lines()   # populated with real hardware info
        self.query_one("#press-key").display = False
        self.set_interval(0.08, self._animate_step)

    async def _animate_step(self) -> None:
        """Called every 80ms to advance the animation."""
        if self._done or self._skipped:
            return

        self._tick += 1

        # Phase 1: POST lines — stream them in one at a time
        if self._tick <= len(self._post_lines) * 2:
            phase_tick = self._tick // 2
            if phase_tick < len(self._post_lines) and phase_tick != self._post_idx:
                self._post_idx = phase_tick
                accumulated = "\n".join(self._post_lines[: self._post_idx + 1])
                self.query_one("#post-lines", Static).update(accumulated)
            return

        # Phase 2: Progress bar
        progress_tick = self._tick - len(self._post_lines) * 2
        if progress_tick <= 30:
            self._progress = min(100, int(progress_tick / 30 * 100))
            msg_idx = min(
                int(progress_tick / 30 * len(PROGRESS_MESSAGES)),
                len(PROGRESS_MESSAGES) - 1,
            )
            spinner = get_spinner_frame(self._tick)
            bar = build_progress_bar(self._progress)
            self.query_one("#progress-area", Static).update(
                f"{spinner} {bar}\n{PROGRESS_MESSAGES[msg_idx]}..."
            )
            return

        # Phase 3: Done — show press any key
        self._done = True
        self.query_one("#progress-area", Static).update(
            f"{build_progress_bar(100)}\nReady."
        )
        self.query_one("#press-key").display = True

    def action_skip(self) -> None:
        """Skip boot animation and go to home."""
        self._skipped = True
        self._go_home()

    def on_key(self, event) -> None:
        """Any key press skips when boot is done, or skips immediately."""
        if self._done or self._skipped:
            self._go_home()
        else:
            self._skipped = True
            self._go_home()

    def _go_home(self) -> None:
        from devrecai.tui.screens.home import HomeScreen
        self.app.switch_screen(HomeScreen())
