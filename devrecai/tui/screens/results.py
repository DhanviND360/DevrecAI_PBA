"""
DevRecAI Results Screen.

Main recommendation output:
- Split panel: left = category tabs + scored tool table, right = AI explanation panel
- Color-coded score table (green ≥85, yellow 60-85, red <60)
- AI explanation panel with LLM-powered deep dive on demand (E key)
- LLM picker modal shown before deep dive — choose Ollama or Gemini
- Comparison mode (C key), Export (X key)
"""
from __future__ import annotations

from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from textual.widgets import DataTable, Label, Static, TabbedContent, TabPane, Button, Select
from textual.containers import Horizontal, Vertical, ScrollableContainer


# ─── Category → widget ID helpers ────────────────────────────────────────────

ALL_CATEGORIES = [
    "CI/CD",
    "Observability & Monitoring",
    "Security & Compliance",
    "Infrastructure as Code",
    "Container Orchestration",
    "Artifact Registry",
    "Secrets Management",
    "GitOps",
    "Testing & QA",
    "Service Mesh",
    "Incident Management",
    "Cost Management",
    "API Gateway",
    "Log Management",
]


def _tab_id(cat: str) -> str:
    """Convert a category name to a safe Textual widget ID."""
    return (
        cat.lower()
        .replace(" ", "-")
        .replace("&", "and")
        .replace("/", "-")
        .replace("--", "-")  # ci/cd → ci-cd (no double dash)
    )


def _score_color(score: float) -> str:
    if score >= 85:
        return "bright_green"
    elif score >= 60:
        return "yellow"
    return "red"


def _confidence_text(level: str) -> Text:
    colors = {"HIGH": "bright_green", "MEDIUM": "yellow", "LOW": "red"}
    return Text(level, style=colors.get(level.upper(), "white"))


# ─── LLM Picker Modal ────────────────────────────────────────────────────────


class LLMPickerModal(ModalScreen[str]):
    """A modal dialog allowing the user to pick which LLM to use for deep-dive."""

    CSS = """
    LLMPickerModal {
        align: center middle;
    }

    #llm-picker-box {
        width: 60;
        height: auto;
        background: #0D0D0D;
        border: double #00FF41;
        padding: 1 2;
    }

    #llm-picker-title {
        color: #00CFFF;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }

    #llm-picker-subtitle {
        color: #005F00;
        text-align: center;
        margin-bottom: 1;
    }

    .llm-option-btn {
        width: 100%;
        margin: 0 0 1 0;
        height: 3;
    }

    #btn-ollama {
        background: #001A33;
        color: #00CFFF;
        border: solid #00CFFF;
    }

    #btn-ollama:hover {
        background: #003366;
        color: #39FFFF;
    }

    #btn-gemini {
        background: #1A0033;
        color: #CF9FFF;
        border: solid #9F5FFF;
    }

    #btn-gemini:hover {
        background: #330066;
        color: #FFFFFF;
    }

    #btn-cancel-llm {
        background: #1A0000;
        color: #FF5555;
        border: solid #550000;
    }

    #btn-cancel-llm:hover {
        background: #330000;
    }

    .llm-info {
        color: #005F00;
        margin-bottom: 1;
        text-align: center;
    }

    DataTable {
        height: auto;
        max-height: 12;
        margin-bottom: 1;
        border: solid #003B00;
    }

    DataTable > .datatable--header {
        background: #003B00;
        color: #39FF14;
        text-style: bold;
    }
    """

    LLM_TABLE_DATA = [
        ("Ollama (Local)", "llama3.2:1b", "Offline / Free", "~1-3s", "★★★"),
        ("Gemini 2.5 Flash", "gemini-2.5-flash", "Google Cloud", "~3-8s", "★★★★★"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="llm-picker-box"):
            yield Static("⚡ SELECT AI EXPLAINER", id="llm-picker-title")
            yield Static("Choose which LLM to use for the deep-dive analysis:", id="llm-picker-subtitle")

            # Mini comparison table
            dt = DataTable(id="llm-compare-table", cursor_type="none", show_cursor=False)
            yield dt

            yield Static("🦙  Ollama runs locally on your machine (no internet needed)", classes="llm-info")
            yield Button("🦙  Ollama — llama3.2:1b  (Local, Fast)", id="btn-ollama", classes="llm-option-btn")

            yield Static("✨  Gemini 2.5 Flash — Google's best reasoning model", classes="llm-info")
            yield Button("✨  Gemini 2.5 Flash  (Cloud, Most Accurate)", id="btn-gemini", classes="llm-option-btn")

            yield Button("✗  Cancel", id="btn-cancel-llm", classes="llm-option-btn")

    def on_mount(self) -> None:
        dt = self.query_one("#llm-compare-table", DataTable)
        dt.add_columns("Provider", "Model", "Backend", "Latency", "Quality")
        for row in self.LLM_TABLE_DATA:
            dt.add_row(*row)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-ollama":
            self.dismiss("ollama")
        elif event.button.id == "btn-gemini":
            self.dismiss("gemini")
        else:
            self.dismiss("")


# ─── Screen ──────────────────────────────────────────────────────────────────


class ResultsScreen(Screen):
    """Results display with split panel and interactive exploration."""

    BINDINGS = [
        Binding("e", "explain_selected", "Explain [E]"),
        Binding("c", "comparison_mode", "Compare [C]"),
        Binding("x", "export", "Export [X]"),
        Binding("h", "history", "History [H]"),
        Binding("q", "quit_session", "Back [Q]"),
        Binding("escape", "quit_session", "Back", show=False),
    ]

    CSS = """
    ResultsScreen {
        background: #0A0A0A;
    }

    #results-header {
        background: #003B00;
        color: #00FF41;
        text-style: bold;
        height: 1;
        dock: top;
        padding: 0 2;
    }

    #results-body {
        layout: horizontal;
        width: 100%;
        height: 1fr;
    }

    /* ── Left panel ── */

    #left-panel {
        width: 55%;
        height: 100%;
        border-right: solid #003B00;
    }

    TabbedContent {
        height: 100%;
    }

    TabPane {
        padding: 0;
        height: 100%;
    }

    DataTable {
        height: 100%;
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
    }

    DataTable > .datatable--hover {
        background: #001A00;
    }

    /* ── Right panel ── */

    #right-panel {
        width: 45%;
        height: 100%;
        layout: vertical;
        padding: 0 1;
    }

    #explanation-title {
        color: #00CFFF;
        text-style: bold;
        height: 2;
        padding: 0 1;
    }

    #explanation-scroll {
        width: 100%;
        height: 1fr;
        overflow-y: auto;
        border: solid #003B00;
        padding: 0 1;
    }

    #explanation-body {
        color: #00FF41;
        width: 100%;
    }

    /* ── Bottom bar ── */

    #action-bar {
        background: #001A00;
        color: #005F00;
        height: 1;
        dock: bottom;
        padding: 0 2;
    }

    .no-results { color: #005F00; text-align: center; padding: 2; }
    #error-label { color: #FF3131; padding: 2; }
    """

    def __init__(self, profile: dict, results: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self._profile = profile
        self._results = results
        self._categories_data: dict[str, list[dict]] = results.get("categories", {})
        self._explanations: dict = results.get("explanations", {})
        self._selected_tool: Optional[str] = None
        self._error: str = results.get("error", "")
        # Only include categories that have at least one tool
        self._active_cats: list[str] = [
            c for c in ALL_CATEGORIES if self._categories_data.get(c)
        ]

    def compose(self) -> ComposeResult:
        project = self._profile.get("project_name", "Unnamed Project")
        mode    = self._results.get("metadata", {}).get("mode", "rule_based")
        count   = self._results.get("metadata", {}).get("tool_count", 0)

        yield Static(
            f" DevRecAI Results — {project}  │  Mode: {mode}  │  {count} tools scored",
            id="results-header",
        )

        with Horizontal(id="results-body"):
            # ── Left: tabbed category tables ──────────────────────────────
            with Vertical(id="left-panel"):
                if self._error:
                    yield Label(f"⚠ Engine error: {self._error}", id="error-label")
                elif not self._active_cats:
                    yield Label("No recommendations generated.", classes="no-results")
                else:
                    # KEY FIX: TabbedContent() with NO positional args.
                    # Let TabPane children define all tabs.
                    with TabbedContent():
                        for cat in self._active_cats:
                            tid = _tab_id(cat)
                            with TabPane(cat, id=tid):
                                # One DataTable per tab pane
                                yield DataTable(
                                    id=f"dt-{tid}",
                                    cursor_type="row",
                                    show_cursor=True,
                                )

            # ── Right: AI explanation panel ───────────────────────────────
            with Vertical(id="right-panel"):
                yield Static("[ SELECT A TOOL ]", id="explanation-title")
                with ScrollableContainer(id="explanation-scroll"):
                    yield Static(
                        "← Click a row in the table on the left.\n\n"
                        "  [E]  Deep-dive AI explanation for selected tool\n"
                        "       You'll choose between Ollama (local) or\n"
                        "       Gemini 2.5 Flash (cloud) as the AI backend\n\n"
                        "  [C]  Side-by-side comparison of multiple tools\n"
                        "  [X]  Export full Markdown + PDF report\n"
                        "  [H]  Session history\n"
                        "  [Q]  Back to home menu",
                        id="explanation-body",
                    )

        yield Static(
            " [E] Explain  [C] Compare  [X] Export  [H] History  [Q] Back",
            id="action-bar",
        )

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        """Populate DataTable rows after all widgets are mounted."""
        # call_after_refresh ensures the DOM is fully ready before we query
        self.call_after_refresh(self._populate_all_tables)

    def _populate_all_tables(self) -> None:
        """Add columns + rows to every DataTable in one pass."""
        for cat in self._active_cats:
            tools = self._categories_data.get(cat, [])
            if not tools:
                continue
            tid = _tab_id(cat)
            try:
                dt: DataTable = self.query_one(f"#dt-{tid}", DataTable)
                # Guard: skip if already populated (e.g. screen revisited)
                if dt.columns:
                    continue
                dt.add_columns("Rank", "Tool", "Score /100", "Confidence", "Fit")
                for i, tool in enumerate(tools, 1):
                    score = float(tool.get("score", 0))
                    conf  = str(tool.get("confidence", "MEDIUM"))
                    fit   = str(tool.get("fit_tag", "GOOD FIT"))
                    name  = str(tool.get("name", "Unknown"))
                    dt.add_row(
                        Text(f"#{i}", style="bold cyan"),
                        Text(name, style="bold white"),
                        Text(f"{score:.0f}", style=_score_color(score)),
                        _confidence_text(conf),
                        Text(fit, style="bright_green" if "NATIVE" in fit else "yellow"),
                        key=name,   # row key = tool name for easy retrieval
                    )
            except Exception as exc:
                # Surface the error in the explanation panel so we can debug
                try:
                    self.query_one("#explanation-body", Static).update(
                        f"[DataTable error for {cat}]: {exc}\n\n"
                        "Please report this bug."
                    )
                except Exception:
                    pass

    # ─── Row selection ────────────────────────────────────────────────────────

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Show explanation for selected tool when user clicks or presses Enter."""
        try:
            # row_key.value is the `key=name` string we passed to add_row
            tool_name = str(event.row_key.value)
            self._selected_tool = tool_name
            self._show_explanation(tool_name)
        except Exception as exc:
            self.query_one("#explanation-body", Static).update(f"Selection error: {exc}")

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Preview tool name in title as user navigates rows with arrow keys."""
        try:
            tool_name = str(event.row_key.value)
            self._selected_tool = tool_name
            self.query_one("#explanation-title", Static).update(
                f"[ {tool_name.upper()} ]\nPress [E] for AI explanation"
            )
        except Exception:
            pass

    def _show_explanation(self, tool_name: str) -> None:
        """Render stored LLM explanation in the right panel."""
        expl = self._explanations.get(tool_name)

        if isinstance(expl, dict) and expl:
            lines = [
                f"Tool: {tool_name}",
                "═" * 38,
                "",
                "✓ FIT SUMMARY",
                expl.get("fit_summary", "N/A"),
                "",
                "⚙ INTEGRATION NOTES",
                expl.get("integration_notes", "N/A"),
                "",
                "⚠ RISKS",
                expl.get("risks", "N/A"),
                "",
                "📊 MATURITY REQUIRED",
                expl.get("maturity_required", "N/A"),
                "",
                f"🎯 CONFIDENCE: {expl.get('confidence_level', 'MEDIUM')}",
            ]
        else:
            lines = [
                f"Tool: {tool_name}",
                "═" * 38,
                "",
                f"No pre-generated explanation for {tool_name}.",
                "",
                "Press [E] to query an LLM for a",
                "detailed deep-dive explanation.",
                "",
                "You will be prompted to choose:",
                "  🦙  Ollama (llama3.2:1b) — local",
                "  ✨  Gemini 2.5 Flash      — cloud",
                "",
                "(This may take 10-30 seconds depending",
                "on your AI backend choice.)",
            ]

        try:
            self.query_one("#explanation-body", Static).update("\n".join(lines))
            self.query_one("#explanation-title", Static).update(
                f"[ {tool_name.upper()} ]"
            )
        except Exception:
            pass

    # ─── Keybinding actions ───────────────────────────────────────────────────

    def action_explain_selected(self) -> None:
        """Show LLM picker modal, then run deep dive with chosen provider."""
        if not self._selected_tool:
            try:
                self.query_one("#explanation-body", Static).update(
                    "No tool selected.\n\nClick or navigate to a row in the table first."
                )
            except Exception:
                pass
            return
        # Push the LLM picker modal and handle its result
        self.app.push_screen(LLMPickerModal(), self._on_llm_picked)

    def _on_llm_picked(self, provider: str) -> None:
        """Callback from LLMPickerModal. Launch deep dive with selected provider."""
        if not provider:
            return  # User cancelled
        tool = self._selected_tool
        if tool:
            self.run_worker(
                self._do_deep_dive(tool, provider),
                exclusive=False,
            )

    async def _do_deep_dive(self, tool_name: str, provider: str) -> None:
        """Async LLM call for single-tool deep dive (runs in worker thread)."""
        provider_label = {
            "ollama": "🦙 Ollama (llama3.2:1b)",
            "gemini": "✨ Gemini 2.5 Flash",
        }.get(provider, provider)
        try:
            self.query_one("#explanation-body", Static).update(
                f"Querying {provider_label} for: {tool_name}\n\n"
                "This may take 10-30 seconds..."
            )
            from devrecai.llm.client import LLMClient
            from devrecai.llm.prompts import build_single_tool_deep_dive_prompt
            from devrecai.llm.explainer import _extract_json

            client = LLMClient(provider_override=provider)
            # Find the tool's score from our results
            score = 0.0
            for cat_tools in self._categories_data.values():
                for t in cat_tools:
                    if t.get("name") == tool_name:
                        score = float(t.get("score", 0))
                        break

            prompt = build_single_tool_deep_dive_prompt(self._profile, tool_name, score)
            response = await client.complete(prompt, max_tokens=2048)
            data = _extract_json(response)
            if not isinstance(data, dict) or not data:
                data = {"fit_summary": response, "confidence_level": "MEDIUM"}
            data["_llm_provider"] = provider_label
            self._explanations[tool_name] = data
            self._show_explanation(tool_name)

            # Update title to show which LLM was used
            try:
                self.query_one("#explanation-title", Static).update(
                    f"[ {tool_name.upper()} ] — via {provider_label}"
                )
            except Exception:
                pass
        except Exception as e:
            try:
                self.query_one("#explanation-body", Static).update(
                    f"LLM error ({provider}): {e}\n\n"
                    "• For Ollama: make sure Ollama is running (ollama serve)\n"
                    "  and llama3.2:1b is pulled (ollama pull llama3.2:1b)\n"
                    "• For Gemini: check your internet connection"
                )
            except Exception:
                pass

    def action_comparison_mode(self) -> None:
        from devrecai.tui.screens.comparison import ComparisonScreen
        self.app.push_screen(ComparisonScreen(profile=self._profile, results=self._results))

    def action_export(self) -> None:
        from devrecai.tui.screens.export_screen import ExportScreen
        self.app.push_screen(ExportScreen(profile=self._profile, results=self._results))

    def action_history(self) -> None:
        from devrecai.tui.screens.history import HistoryScreen
        self.app.push_screen(HistoryScreen())

    def action_quit_session(self) -> None:
        from devrecai.tui.screens.home import HomeScreen
        self.app.switch_screen(HomeScreen())
