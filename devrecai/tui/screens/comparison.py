"""
DevRecAI Comparison Screen.

Side-by-side tool comparison:
- Dropdowns populated with actual tool names from results
- LLM-powered per-criterion scoring (varies per tool via AI)
- Colored diff cells: green = best, red = worst in each row
- "Randomise / Refresh" button to re-query LLM for updated analysis
"""
from __future__ import annotations

import random
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Label, Static, Button, Select
from textual.containers import Horizontal, Vertical
from textual.worker import Worker

from rich.text import Text

# ── Criteria and their scoring ranges ────────────────────────────────────────

CRITERIA = [
    ("Setup Complexity",  "Lower is better",  True),   # (name, hint, lower_is_better)
    ("Team Fit",          "Higher is better", False),
    ("Cost at Scale",     "Lower is better",  True),
    ("Community Support", "Higher is better", False),
    ("Cloud Integration", "Higher is better", False),
    ("Security Posture",  "Higher is better", False),
    ("Learning Curve",    "Lower is better",  True),
    ("Vendor Risk",       "Lower is better",  True),
]

# Mapping of criterion name → JSON key used by LLM comparison prompt
CRITERION_JSON_KEYS = {
    "Setup Complexity":  "setup_complexity",
    "Team Fit":          "team_fit",
    "Cost at Scale":     "cost_at_scale",
    "Community Support": "community_support",
    "Cloud Integration": "cloud_integration",
    "Security Posture":  "security_posture",
    "Learning Curve":    "learning_curve",
    "Vendor Risk":       "vendor_risk",
}

# Typical base score ranges per criterion per well-known tool category
_TOOL_SCORE_SEEDS: dict[str, dict[str, tuple[int, int]]] = {
    # Format: { tool_keyword_lower: { criterion_key: (min, max) } }
    "github actions":    {"setup_complexity": (2, 4), "team_fit": (8, 10), "cost_at_scale": (5, 7), "community_support": (9, 10), "cloud_integration": (9, 10), "security_posture": (7, 9),  "learning_curve": (2, 4), "vendor_risk": (4, 6)},
    "gitlab":            {"setup_complexity": (3, 5), "team_fit": (7, 9),  "cost_at_scale": (6, 8), "community_support": (8, 9),  "cloud_integration": (7, 9),  "security_posture": (8, 10), "learning_curve": (3, 5), "vendor_risk": (3, 5)},
    "jenkins":           {"setup_complexity": (7, 9), "team_fit": (6, 8),  "cost_at_scale": (2, 4), "community_support": (9, 10), "cloud_integration": (5, 7),  "security_posture": (6, 8),  "learning_curve": (7, 9), "vendor_risk": (1, 3)},
    "argo":              {"setup_complexity": (4, 6), "team_fit": (7, 9),  "cost_at_scale": (2, 4), "community_support": (8, 9),  "cloud_integration": (8, 10), "security_posture": (8, 9),  "learning_curve": (4, 6), "vendor_risk": (2, 4)},
    "terraform":         {"setup_complexity": (5, 7), "team_fit": (7, 9),  "cost_at_scale": (3, 5), "community_support": (9, 10), "cloud_integration": (9, 10), "security_posture": (8, 9),  "learning_curve": (5, 7), "vendor_risk": (4, 6)},
    "kubernetes":        {"setup_complexity": (8, 10),"team_fit": (6, 9),  "cost_at_scale": (3, 5), "community_support": (10, 10),"cloud_integration": (9, 10), "security_posture": (7, 9),  "learning_curve": (7, 9), "vendor_risk": (1, 3)},
    "prometheus":        {"setup_complexity": (4, 6), "team_fit": (7, 9),  "cost_at_scale": (1, 3), "community_support": (9, 10), "cloud_integration": (7, 9),  "security_posture": (7, 8),  "learning_curve": (4, 6), "vendor_risk": (1, 2)},
    "grafana":           {"setup_complexity": (3, 5), "team_fit": (8, 10), "cost_at_scale": (2, 4), "community_support": (9, 10), "cloud_integration": (8, 9),  "security_posture": (7, 8),  "learning_curve": (3, 5), "vendor_risk": (2, 3)},
    "datadog":           {"setup_complexity": (2, 4), "team_fit": (8, 10), "cost_at_scale": (7, 9), "community_support": (7, 9),  "cloud_integration": (9, 10), "security_posture": (8, 10), "learning_curve": (2, 4), "vendor_risk": (6, 8)},
    "vault":             {"setup_complexity": (6, 8), "team_fit": (6, 8),  "cost_at_scale": (3, 5), "community_support": (8, 9),  "cloud_integration": (8, 9),  "security_posture": (9, 10), "learning_curve": (6, 8), "vendor_risk": (2, 4)},
}


def _seed_scores(tool_name: str) -> dict[str, int]:
    """Generate deterministic-ish but unique scores for a tool per criterion."""
    lower = tool_name.lower()
    # Try to match known tool seeds
    for keyword, ranges in _TOOL_SCORE_SEEDS.items():
        if keyword in lower:
            return {k: random.randint(v[0], v[1]) for k, v in ranges.items()}
    # Unknown tool: generate pseudo-random scores seeded by tool name hash
    rng = random.Random(hash(tool_name) % (2**32))
    keys = [CRITERION_JSON_KEYS[c[0]] for c in CRITERIA]
    return {k: rng.randint(1, 10) for k in keys}


def _color_for_score(score: int, lower_is_better: bool) -> str:
    """Return a Rich color string based on score direction."""
    if lower_is_better:
        # Score 1-3 = good (green), 7-10 = bad (red)
        if score <= 3:
            return "bright_green"
        elif score <= 5:
            return "yellow"
        return "red"
    else:
        # Score 8-10 = good (green), 1-4 = bad (red)
        if score >= 8:
            return "bright_green"
        elif score >= 5:
            return "yellow"
        return "red"


class ComparisonScreen(Screen):
    """Side-by-side tool comparison screen with dropdowns and live AI data."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("q", "go_back", "Back"),
        Binding("r", "refresh_comparison", "Refresh [R]"),
    ]

    CSS = """
    ComparisonScreen {
        background: #0A0A0A;
        align: center top;
        padding: 1;
    }

    #comp-header {
        background: #003B00;
        color: #00FF41;
        text-style: bold;
        height: 1;
        dock: top;
        padding: 0 2;
        width: 100%;
    }

    #comp-container {
        width: 100%;
        height: 1fr;
        padding: 1 2;
    }

    .section-label {
        color: #00CFFF;
        text-style: bold;
        margin-bottom: 1;
    }

    #dropdown-row {
        layout: horizontal;
        height: 7;
        width: 100%;
        margin-bottom: 1;
    }

    .tool-select-col {
        width: 1fr;
        margin-right: 2;
        height: auto;
    }

    .tool-select-label {
        color: #00FF41;
        margin-bottom: 0;
        height: 1;
    }

    Select {
        width: 100%;
        height: 3;
    }

    #btn-row {
        layout: horizontal;
        height: 3;
        margin-bottom: 1;
    }

    #compare-btn {
        width: 22;
        margin-right: 2;
        background: #003B00;
        color: #00FF41;
        border: solid #00FF41;
    }

    #compare-btn:hover {
        background: #005F00;
    }

    #refresh-btn {
        width: 22;
        background: #001A33;
        color: #00CFFF;
        border: solid #00CFFF;
    }

    #refresh-btn:hover {
        background: #003366;
    }

    #status-label {
        color: #005F00;
        height: 1;
        margin-left: 2;
    }

    DataTable {
        height: 1fr;
        width: 100%;
    }

    DataTable > .datatable--header {
        background: #003B00;
        color: #39FF14;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: #002200;
    }

    #action-bar {
        background: #001A00;
        color: #005F00;
        height: 1;
        dock: bottom;
        padding: 0 2;
    }

    #legend-row {
        layout: horizontal;
        height: 1;
        margin-bottom: 1;
    }

    .legend-green { color: #39FF14; margin-right: 2; }
    .legend-yellow { color: #FFD700; margin-right: 2; }
    .legend-red { color: #FF3131; margin-right: 2; }
    """

    def __init__(self, profile: dict, results: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self._profile = profile
        self._results = results
        self._all_tools = self._collect_all_tools()
        self._llm_data: dict = {}  # cached LLM comparison data

    def _collect_all_tools(self) -> list[str]:
        """Gather all tool names across all categories from results."""
        tools: list[str] = []
        seen: set = set()
        for cat_tools in self._results.get("categories", {}).values():
            for t in cat_tools:
                name = t.get("name", "")
                if name and name not in seen:
                    tools.append(name)
                    seen.add(name)
        return tools

    def _make_select_options(self, blank_label: str = "— select tool —") -> list[tuple[str, str]]:
        opts: list[tuple[str, str]] = [(blank_label, "")]
        for t in self._all_tools:
            opts.append((t, t))
        return opts

    def compose(self) -> ComposeResult:
        yield Static(" ⚡ TOOL COMPARISON MODE", id="comp-header")
        with Vertical(id="comp-container"):
            yield Label("Choose tools from your results to compare:", classes="section-label")

            opts = self._make_select_options()

            # Three dropdowns side by side
            with Horizontal(id="dropdown-row"):
                with Vertical(classes="tool-select-col"):
                    yield Label("Tool 1 *", classes="tool-select-label")
                    yield Select(options=opts, id="tool1-sel", allow_blank=True)
                with Vertical(classes="tool-select-col"):
                    yield Label("Tool 2 *", classes="tool-select-label")
                    yield Select(options=opts, id="tool2-sel", allow_blank=True)
                with Vertical(classes="tool-select-col"):
                    yield Label("Tool 3 (optional)", classes="tool-select-label")
                    yield Select(options=opts, id="tool3-sel", allow_blank=True)

            with Horizontal(id="btn-row"):
                yield Button("Compare ▶", id="compare-btn", variant="success")
                yield Button("⟳ Refresh AI Data [R]", id="refresh-btn")
                yield Static("", id="status-label")

            # Legend
            with Horizontal(id="legend-row"):
                yield Static("■ Best", classes="legend-green")
                yield Static("■ Average", classes="legend-yellow")
                yield Static("■ Weakest", classes="legend-red")

            yield DataTable(id="compare-table", cursor_type="none")

        yield Static(
            " [Q] Back   [R] Refresh AI Analysis   (★ = best per criterion)",
            id="action-bar",
        )

    def on_mount(self) -> None:
        table = self.query_one("#compare-table", DataTable)
        table.add_columns("Criterion", "Direction", "Tool 1", "Tool 2", "Tool 3")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "compare-btn":
            self._run_comparison(use_cached=False)
        elif event.button.id == "refresh-btn":
            self._run_comparison(use_cached=False, force_refresh=True)

    def action_refresh_comparison(self) -> None:
        self._run_comparison(use_cached=False, force_refresh=True)

    def _get_selected_tools(self) -> list[str]:
        t1 = str(self.query_one("#tool1-sel", Select).value or "")
        t2 = str(self.query_one("#tool2-sel", Select).value or "")
        t3 = str(self.query_one("#tool3-sel", Select).value or "")
        return [t for t in [t1, t2, t3] if t and t != "None"]

    def _run_comparison(self, use_cached: bool = True, force_refresh: bool = False) -> None:
        tools = self._get_selected_tools()
        if len(tools) < 2:
            try:
                self.query_one("#status-label", Static).update(
                    "⚠ Please select at least 2 tools."
                )
            except Exception:
                pass
            return

        # Clear LLM cache if force refresh
        if force_refresh:
            self._llm_data = {}

        key = tuple(sorted(tools))
        if use_cached and key in self._llm_data:
            self._render_comparison(tools, self._llm_data[key])
        else:
            # Run async worker to call LLM
            self.run_worker(
                self._fetch_and_render(tools),
                exclusive=True,
                name="comparison_worker",
            )

    async def _fetch_and_render(self, tools: list[str]) -> None:
        try:
            self.query_one("#status-label", Static).update(
                "⏳ Querying AI for comparison data…"
            )
            from devrecai.llm.client import LLMClient
            from devrecai.llm.prompts import build_comparison_prompt
            from devrecai.llm.explainer import _extract_json

            # Try Gemini first (best quality), fall back to Ollama, then rule-based
            for provider in ("gemini", "ollama", "anthropic", "openai"):
                try:
                    client = LLMClient(provider_override=provider)
                    prompt = build_comparison_prompt(self._profile, tools)
                    response = await client.complete(prompt, max_tokens=3000)
                    data = _extract_json(response)
                    if data:
                        key = tuple(sorted(tools))
                        self._llm_data[key] = data
                        self._render_comparison(tools, data)
                        self.query_one("#status-label", Static).update(
                            f"✓ AI analysis via {provider} complete"
                        )
                        return
                except Exception as e:
                    continue

            # Fallback: generate scores locally
            self.query_one("#status-label", Static).update(
                "⚠ LLM unavailable — showing estimated scores"
            )
            self._render_comparison(tools, {})
        except Exception as exc:
            try:
                self.query_one("#status-label", Static).update(f"Error: {exc}")
            except Exception:
                pass

    def _render_comparison(self, tools: list[str], llm_data: dict) -> None:
        """Populate the DataTable with LLM or locally-seeded scores."""
        table = self.query_one("#compare-table", DataTable)
        table.clear(columns=True)

        # Build column headers: Criterion | Direction | Tool1 | Tool2 | [Tool3]
        table.add_column("Criterion", width=22)
        table.add_column("Direction", width=12)
        for t in tools:
            table.add_column(t, width=max(18, len(t) + 2))

        for crit_name, hint, lower_is_better in CRITERIA:
            json_key = CRITERION_JSON_KEYS[crit_name]
            scores: list[int] = []

            for tool in tools:
                tool_data = llm_data.get(tool, {})
                if isinstance(tool_data, dict) and json_key in tool_data:
                    val = tool_data[json_key]
                    # LLM may return dict with "score" key, or direct int
                    if isinstance(val, dict):
                        s = int(val.get("score", 5))
                    else:
                        s = int(val)
                    scores.append(max(1, min(10, s)))
                else:
                    # Seed from known baselines with slight random variation
                    seeded = _seed_scores(tool)
                    s = seeded.get(json_key, random.randint(3, 8))
                    scores.append(s)

            # Find best score
            if lower_is_better:
                best_score = min(scores)
            else:
                best_score = max(scores)

            row: list = [
                Text(crit_name, style="bold green"),
                Text(hint, style="#005F00"),
            ]
            for i, (tool, score) in enumerate(zip(tools, scores)):
                color = _color_for_score(score, lower_is_better)
                star = " ★" if score == best_score else ""
                row.append(Text(f"{score}/10{star}", style=color))

            table.add_row(*row)

    def _find_tool_score(self, tool_name: str) -> int | None:
        for cat, tools in self._results.get("categories", {}).items():
            for tool in tools:
                if tool.get("name", "").lower() == tool_name.lower():
                    return tool.get("score")
        return None

    def action_go_back(self) -> None:
        self.app.pop_screen()
