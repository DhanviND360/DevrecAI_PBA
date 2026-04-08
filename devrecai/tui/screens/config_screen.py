"""
DevRecAI Config Screen.

Interactive settings editor:
- LLM Provider selection (Ollama / Gemini / OpenAI / Anthropic / Custom)
- API Key input (masked)
- Model selection
- Output directory
- Scorer mode (Rule-based / ML / Hybrid)
- Theme toggle (applied live to the running app)
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static, Switch
from textual.containers import Horizontal, Vertical, ScrollableContainer

from devrecai.config.settings import get_settings, reload_settings


# ── Theme CSS definitions ─────────────────────────────────────────────────────

THEME_CSS: dict[str, str] = {
    "retro-green": """
        Screen { background: #0A0A0A; color: #00FF41; }
        * { scrollbar-color: #00FF41; scrollbar-background: #0A0A0A; }
        .panel { border: solid #003B00; background: #0D0D0D; }
        .section-header, .status-bar, .status-bar-top { background: #003B00; color: #00FF41; }
        Button { background: #003B00; color: #00FF41; border: solid #00FF41; }
        Button:hover { background: #005F00; color: #39FF14; }
        Button:focus { background: #00FF41; color: #0A0A0A; }
        Input { background: #0D0D0D; color: #00FF41; border: solid #003B00; }
        Input:focus { border: solid #00FF41; background: #111111; }
        Select { background: #0D0D0D; color: #00FF41; border: solid #003B00; }
        DataTable { background: #0A0A0A; color: #00FF41; }
        DataTable > .datatable--header { background: #003B00; color: #39FF14; }
        DataTable > .datatable--cursor { background: #005F00; color: #39FF14; }
        Tab { color: #005F00; }
        Tab.-active { color: #00FF41; background: #003B00; text-style: bold; }
        Label { color: #00FF41; }
    """,
    "amber": """
        Screen { background: #0A0800; color: #FFB300; }
        * { scrollbar-color: #FFB300; scrollbar-background: #0A0800; }
        .panel { border: solid #3B2800; background: #0D0B00; }
        .section-header, .status-bar, .status-bar-top { background: #3B2800; color: #FFB300; }
        Button { background: #3B2800; color: #FFB300; border: solid #FFB300; }
        Button:hover { background: #5F4000; color: #FFC733; }
        Button:focus { background: #FFB300; color: #0A0800; }
        Input { background: #0D0B00; color: #FFB300; border: solid #3B2800; }
        Input:focus { border: solid #FFB300; background: #111000; }
        Select { background: #0D0B00; color: #FFB300; border: solid #3B2800; }
        DataTable { background: #0A0800; color: #FFB300; }
        DataTable > .datatable--header { background: #3B2800; color: #FFC733; }
        DataTable > .datatable--cursor { background: #5F4000; color: #FFC733; }
        Tab { color: #5F4000; }
        Tab.-active { color: #FFB300; background: #3B2800; text-style: bold; }
        Label { color: #FFB300; }
    """,
    "ice-blue": """
        Screen { background: #00080A; color: #00CFFF; }
        * { scrollbar-color: #00CFFF; scrollbar-background: #00080A; }
        .panel { border: solid #003B4A; background: #000D10; }
        .section-header, .status-bar, .status-bar-top { background: #003B4A; color: #00CFFF; }
        Button { background: #003B4A; color: #00CFFF; border: solid #00CFFF; }
        Button:hover { background: #005F77; color: #39FFFF; }
        Button:focus { background: #00CFFF; color: #00080A; }
        Input { background: #000D10; color: #00CFFF; border: solid #003B4A; }
        Input:focus { border: solid #00CFFF; background: #001015; }
        Select { background: #000D10; color: #00CFFF; border: solid #003B4A; }
        DataTable { background: #00080A; color: #00CFFF; }
        DataTable > .datatable--header { background: #003B4A; color: #39FFFF; }
        DataTable > .datatable--cursor { background: #005F77; color: #39FFFF; }
        Tab { color: #005F77; }
        Tab.-active { color: #00CFFF; background: #003B4A; text-style: bold; }
        Label { color: #00CFFF; }
    """,
    "ghost-white": """
        Screen { background: #111111; color: #E8E8E8; }
        * { scrollbar-color: #888888; scrollbar-background: #111111; }
        .panel { border: solid #333333; background: #1A1A1A; }
        .section-header, .status-bar, .status-bar-top { background: #222222; color: #E8E8E8; }
        Button { background: #222222; color: #E8E8E8; border: solid #888888; }
        Button:hover { background: #333333; color: #FFFFFF; }
        Button:focus { background: #888888; color: #111111; }
        Input { background: #1A1A1A; color: #E8E8E8; border: solid #333333; }
        Input:focus { border: solid #888888; background: #222222; }
        Select { background: #1A1A1A; color: #E8E8E8; border: solid #333333; }
        DataTable { background: #111111; color: #E8E8E8; }
        DataTable > .datatable--header { background: #222222; color: #FFFFFF; }
        DataTable > .datatable--cursor { background: #333333; color: #FFFFFF; }
        Tab { color: #555555; }
        Tab.-active { color: #E8E8E8; background: #222222; text-style: bold; }
        Label { color: #E8E8E8; }
    """,
}


class ConfigScreen(Screen):
    """Settings management TUI screen."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("ctrl+s", "save_config", "Save"),
        Binding("q", "go_back", "Back"),
    ]

    CSS = """
    ConfigScreen {
        background: #0A0A0A;
        align: center top;
        padding: 1;
    }

    #config-header {
        background: #003B00;
        color: #00FF41;
        text-style: bold;
        height: 1;
        dock: top;
        padding: 0 2;
    }

    #config-scroll {
        width: 100%;
        height: 1fr;
        align: center top;
    }

    #config-container {
        width: 80;
        height: auto;
        border: double #003B00;
        padding: 1 3;
        margin-top: 1;
    }

    .section-title {
        color: #00CFFF;
        text-style: bold;
        margin: 1 0 0 0;
        border-bottom: solid #003B00;
    }

    .field-label {
        color: #00FF41;
        margin-top: 1;
    }

    Input {
        width: 100%;
        margin: 0 0 1 0;
    }

    Select {
        width: 100%;
        margin: 0 0 1 0;
    }

    #btn-row {
        layout: horizontal;
        margin-top: 2;
        height: 3;
    }

    Button {
        width: 20;
        margin-right: 2;
    }

    #save-msg {
        color: #39FF14;
        margin-top: 1;
    }

    .hint-text {
        color: #005F00;
        margin-bottom: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._settings = get_settings()

    def compose(self) -> ComposeResult:
        cfg = self._settings
        yield Static(
            " CONFIGURATION — DevRecAI",
            id="config-header",
        )
        with ScrollableContainer(id="config-scroll"):
            with Vertical(id="config-container"):
                # ── LLM Provider ──────────────────────────────────────────
                yield Label("═══ LLM PROVIDER ═══", classes="section-title")
                yield Label("Provider:", classes="field-label")
                yield Select(
                    [
                        ("🦙  Ollama — llama3.2:1b (Local, Free)", "ollama"),
                        ("✨  Gemini 2.5 Flash (Google Cloud)", "gemini"),
                        ("Anthropic — Claude", "anthropic"),
                        ("OpenAI — GPT", "openai"),
                        ("Custom / Local OpenAI-compatible", "custom"),
                    ],
                    value=cfg.llm.provider,
                    id="llm-provider",
                )
                yield Label(
                    "Note: Ollama uses llama3.2:1b locally. Gemini uses the built-in API key.",
                    classes="hint-text",
                )
                yield Label("Model (for Anthropic/OpenAI/Custom):", classes="field-label")
                yield Input(
                    value=cfg.llm.model,
                    placeholder="claude-sonnet-4-20250514 / gpt-4o / custom",
                    id="llm-model",
                )
                yield Label("API Key Env Var (for Anthropic/OpenAI/Custom):", classes="field-label")
                yield Input(
                    value=cfg.llm.api_key_env,
                    placeholder="ANTHROPIC_API_KEY",
                    id="api-key-env",
                )

                # ── Scorer ────────────────────────────────────────────────
                yield Label("═══ SCORER ═══", classes="section-title")
                yield Label("Scorer Mode:", classes="field-label")
                yield Select(
                    [
                        ("Hybrid (default — ML + rule blend)", "hybrid"),
                        ("Rule-based (deterministic, offline)", "rule_based"),
                        ("ML Model (XGBoost)", "ml_model"),
                    ],
                    value=cfg.scorer.mode,
                    id="scorer-mode",
                )

                # ── Output ────────────────────────────────────────────────
                yield Label("═══ OUTPUT ═══", classes="section-title")
                yield Label("Report Output Directory:", classes="field-label")
                yield Input(
                    value=cfg.output.directory,
                    placeholder="~/devrec-reports/",
                    id="output-dir",
                )

                # ── Theme ─────────────────────────────────────────────────
                yield Label("═══ THEME ═══", classes="section-title")
                yield Label("Terminal Theme (applied immediately on Save):", classes="field-label")
                yield Select(
                    [
                        ("Retro Green (default)", "retro-green"),
                        ("Amber", "amber"),
                        ("Ice Blue", "ice-blue"),
                        ("Ghost White", "ghost-white"),
                    ],
                    value=cfg.theme.name,
                    id="theme-name",
                )

                with Horizontal(id="btn-row"):
                    yield Button("Save [Ctrl+S]", id="btn-save", variant="success")
                    yield Button("Cancel [Q]", id="btn-cancel", variant="default")
                yield Static("", id="save-msg")

    def action_save_config(self) -> None:
        self._save()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._save()
        elif event.button.id == "btn-cancel":
            self.action_go_back()

    def _save(self) -> None:
        try:
            cfg = self._settings
            cfg.llm.provider = str(self.query_one("#llm-provider", Select).value)
            cfg.llm.model = self.query_one("#llm-model", Input).value.strip()
            cfg.llm.api_key_env = self.query_one("#api-key-env", Input).value.strip()
            cfg.scorer.mode = str(self.query_one("#scorer-mode", Select).value)
            cfg.output.directory = self.query_one("#output-dir", Input).value.strip()
            new_theme = str(self.query_one("#theme-name", Select).value)
            cfg.theme.name = new_theme  # type: ignore[assignment]
            cfg.save()
            reload_settings()

            # Apply the theme CSS live to the running app
            self._apply_theme(new_theme)

            self.query_one("#save-msg", Static).update(
                f"✓ Configuration saved! Theme '{new_theme}' applied."
            )
        except Exception as e:
            self.query_one("#save-msg", Static).update(f"✗ Save failed: {e}")

    def _apply_theme(self, theme_name: str) -> None:
        """Inject theme CSS into the running Textual app."""
        css = THEME_CSS.get(theme_name)
        if css:
            try:
                # Textual apps expose .stylesheet which we can reparse at runtime.
                # We overwrite the app's global CSS string and force a refresh.
                self.app.CSS = css
                # Trigger a stylesheet reload
                self.app.refresh_css()
            except Exception:
                pass
