"""
DevRecAI Processing Screen.

Shown while the LLM and scorer are running:
- Large animated ASCII spinner
- Cycling status messages
- Elapsed time counter
"""
from __future__ import annotations

import asyncio
from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static

STATUS_MESSAGES = [
    "Analysing stack compatibility...",
    "Loading tool knowledge base...",
    "Running rule-based scorer...",
    "Querying LLM for explanations...",
    "Building recommendation matrix...",
    "Scoring 47 DevOps tools...",
    "Evaluating compliance requirements...",
    "Calculating team-size fit...",
    "Estimating vendor lock-in risk...",
    "Generating AI explanations...",
    "Finalising recommendations...",
    "Almost there...",
]

SPINNER = [
    r"""
     ╔══════════════╗
     ║    ██████    ║
     ║   ██    ██   ║
     ║  ██  ██  ██  ║
     ║   ██    ██   ║
     ║    ██████    ║
     ╚══════════════╝
    """,
    r"""
     ╔══════════════╗
     ║   ▄█████▄   ║
     ║  ▀▀▀▀▀▀▀▀▀  ║
     ║  ██  ██  ██  ║
     ║  ▄▄▄▄▄▄▄▄▄  ║
     ║   ▀█████▀   ║
     ╚══════════════╝
    """,
]


class ProcessingScreen(Screen):
    """Processing screen with spinner and status messages."""

    CSS = """
    ProcessingScreen {
        align: center middle;
        background: #0A0A0A;
    }

    #proc-container {
        width: 60;
        height: auto;
        border: double #003B00;
        padding: 2 4;
        align: center middle;
    }

    #proc-title {
        color: #00FF41;
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    #spinner-display {
        color: #39FF14;
        text-align: center;
        width: 100%;
        height: 10;
    }

    #status-msg {
        color: #00CFFF;
        text-align: center;
        width: 100%;
        margin-top: 1;
    }

    #elapsed {
        color: #005F00;
        text-align: center;
        width: 100%;
        margin-top: 1;
    }

    #noise-area {
        color: #001A00;
        width: 100%;
        height: 2;
        text-align: center;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    def __init__(self, profile: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self._profile = profile
        self._tick = 0
        self._start_time = datetime.now()
        self._msg_idx = 0
        self._done = False

    def compose(self) -> ComposeResult:
        with Static(id="proc-container"):
            yield Static("[ DEVRECAI ENGINE ]", id="proc-title")
            yield Static(self._spinner_frame(), id="spinner-display")
            yield Static(STATUS_MESSAGES[0], id="status-msg")
            yield Static("Elapsed: 0s", id="elapsed")
            yield Static("", id="noise-area")

    def on_mount(self) -> None:
        self.set_interval(0.15, self._animate)
        # Use run_worker so the async engine runs in a thread-safe Textual worker
        self.run_worker(self._run_engine, exclusive=True)

    async def _run_engine(self) -> None:
        """Actually run the scoring and LLM pipeline in a Textual worker."""
        try:
            from devrecai.engine.scorer import Scorer
            from devrecai.llm.explainer import Explainer

            scorer = Scorer()
            results = await scorer.score(self._profile)

            explainer = Explainer()
            explanations = await explainer.explain(self._profile, results)
            results["explanations"] = explanations

            self._done = True
            # Save session to DB in background
            self.call_after_refresh(self._navigate_to_results, results)
        except Exception as e:
            self._done = True
            self.call_after_refresh(
                self._navigate_to_results,
                {"error": str(e), "categories": {}, "explanations": {}}
            )

    def _navigate_to_results(self, results: dict) -> None:
        """Called on the UI thread after engine completes."""
        from devrecai.tui.screens.results import ResultsScreen
        self.app.switch_screen(ResultsScreen(profile=self._profile, results=results))

    def _spinner_frame(self) -> str:
        frames = ["|", "/", "—", "\\"]
        big = "  " + frames[self._tick % 4] * 5 + "  "
        border = "═" * 20
        return f"\n  ╔{border}╗\n  ║  {big}  ║\n  ╠{border}╣\n  ║  PROCESSING...  ║\n  ╚{border}╝\n"

    def _animate(self) -> None:
        if self._done:
            return
        self._tick += 1
        # Update spinner
        try:
            self.query_one("#spinner-display", Static).update(self._spinner_frame())
        except Exception:
            pass

        # Cycle status message every ~12 ticks
        if self._tick % 12 == 0:
            self._msg_idx = (self._msg_idx + 1) % len(STATUS_MESSAGES)
            try:
                self.query_one("#status-msg", Static).update(STATUS_MESSAGES[self._msg_idx])
            except Exception:
                pass

        # Elapsed time
        elapsed = int((datetime.now() - self._start_time).total_seconds())
        try:
            self.query_one("#elapsed", Static).update(f"Elapsed: {elapsed}s")
        except Exception:
            pass

    def action_cancel(self) -> None:
        self._done = True
        self.app.pop_screen()
