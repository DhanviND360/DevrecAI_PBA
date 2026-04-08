"""
DevRecAI Home Screen.

Main menu after boot:
- Smaller persistent ASCII logo
- Numbered menu items with highlighted selection
- Bottom status bar (model, LLM provider, date/time)
- Cycling retro tips footer
"""
from __future__ import annotations

import asyncio
from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Label, Static, Footer

from devrecai.config.settings import get_settings
from devrecai.tui.animations.boot_animation import get_random_tip

SMALL_LOGO = r"""
 ██████╗ ███████╗██╗   ██╗██████╗ ███████╗ ██████╗ █████╗ ██╗
 ██╔══██╗██╔════╝██║   ██║██╔══██╗██╔════╝██╔════╝██╔══██╗██║
 ██║  ██║█████╗  ██║   ██║██████╔╝█████╗  ██║     ███████║██║
 ██║  ██║██╔══╝  ╚██╗ ██╔╝██╔══██╗██╔══╝  ██║     ██╔══██║██║
 ██████╔╝███████╗ ╚████╔╝ ██║  ██║███████╗╚██████╗██║  ██║██║
 ╚═════╝ ╚══════╝  ╚═══╝  ╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝
        AI-Powered DevOps Tool Recommendation Engine
"""

MENU_ITEMS = [
    ("[1] New Session", "wizard"),
    ("[2] Session History", "history"),
    ("[3] Configuration", "config"),
    ("[4] Exit", "exit"),
]


class HomeScreen(Screen):
    """Main menu screen."""

    BINDINGS = [
        Binding("1", "new_session", "New Session"),
        Binding("2", "history", "History"),
        Binding("3", "config", "Config"),
        Binding("4", "quit", "Exit"),
        Binding("q", "quit", "Exit"),
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("enter", "select_item", "Select", show=False),
    ]

    CSS = """
    HomeScreen {
        align: center middle;
        background: #0A0A0A;
    }

    #home-container {
        width: 80;
        height: auto;
        border: double #003B00;
        padding: 1 4;
    }

    #logo {
        color: #00FF41;
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    #divider {
        color: #003B00;
        text-align: center;
        width: 100%;
    }

    #menu-area {
        width: 100%;
        margin: 1 0;
        padding: 0 8;
    }

    .menu-entry {
        color: #005F00;
        padding: 0 2;
        height: 2;
    }
    .menu-entry.selected {
        color: #39FF14;
        text-style: bold reverse;
    }

    #status-bar {
        color: #003B00;
        text-align: center;
        border-top: solid #003B00;
        margin-top: 1;
        padding-top: 1;
        width: 100%;
    }

    #tip-bar {
        color: #005F00;
        text-style: italic;
        text-align: center;
        margin-top: 1;
        width: 100%;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._selected = 0
        self._settings = get_settings()

    def compose(self) -> ComposeResult:
        with Static(id="home-container"):
            yield Static(SMALL_LOGO, id="logo")
            yield Static("═" * 72, id="divider")
            with Static(id="menu-area"):
                for i, (label, _) in enumerate(MENU_ITEMS):
                    cls = "menu-entry selected" if i == 0 else "menu-entry"
                    yield Label(f"  {label}", id=f"menu-{i}", classes=cls)
            yield Static(self._status_text(), id="status-bar")
            yield Static(get_random_tip(), id="tip-bar")

    def on_mount(self) -> None:
        self.set_interval(5.0, self._cycle_tip)

    def _status_text(self) -> str:
        cfg = self._settings
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        provider = cfg.llm.provider.upper()
        model = cfg.llm.model
        mode = cfg.scorer.mode.replace("_", "-")
        return f"● {provider} / {model}  │  Scorer: {mode}  │  {now}"

    def _cycle_tip(self) -> None:
        try:
            self.query_one("#tip-bar", Static).update(get_random_tip())
        except Exception:
            pass

    def _refresh_menu(self) -> None:
        for i in range(len(MENU_ITEMS)):
            label = self.query_one(f"#menu-{i}", Label)
            text = MENU_ITEMS[i][0]
            if i == self._selected:
                label.update(f"▶ {text}")
                label.set_classes("menu-entry selected")
            else:
                label.update(f"  {text}")
                label.set_classes("menu-entry")

    def action_move_up(self) -> None:
        self._selected = (self._selected - 1) % len(MENU_ITEMS)
        self._refresh_menu()

    def action_move_down(self) -> None:
        self._selected = (self._selected + 1) % len(MENU_ITEMS)
        self._refresh_menu()

    def action_select_item(self) -> None:
        _, action = MENU_ITEMS[self._selected]
        self._activate(action)

    def action_new_session(self) -> None:
        self._activate("wizard")

    def action_history(self) -> None:
        self._activate("history")

    def action_config(self) -> None:
        self._activate("config")

    def action_quit(self) -> None:
        self.app.exit()

    def _activate(self, action: str) -> None:
        if action == "wizard":
            # Show JARVIS animation before entering the input wizard
            from devrecai.tui.screens.jarvis_screen import JarvisScreen
            self.app.push_screen(JarvisScreen())
        elif action == "history":
            from devrecai.tui.screens.history import HistoryScreen
            self.app.push_screen(HistoryScreen())
        elif action == "config":
            from devrecai.tui.screens.config_screen import ConfigScreen
            self.app.push_screen(ConfigScreen())
        elif action == "exit":
            self.app.exit()
