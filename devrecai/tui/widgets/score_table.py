"""
DevRecAI Score Table Widget.

Custom DataTable widget for displaying ranked tool recommendations
with color-coded scores and confidence levels.
"""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable


FIT_TAGS = {
    "NATIVE FIT": "bright_green",
    "STRONG FIT": "green",
    "GOOD FIT": "yellow",
    "MARGINAL FIT": "orange3",
    "POOR FIT": "red",
}


def score_color(score: float) -> str:
    """Return a Rich color string based on score value."""
    if score >= 85:
        return "bright_green"
    elif score >= 60:
        return "yellow"
    else:
        return "red"


def confidence_markup(level: str) -> Text:
    """Return colored Rich Text for confidence level."""
    colors = {"HIGH": "bright_green", "MEDIUM": "yellow", "LOW": "red"}
    color = colors.get(level.upper(), "white")
    return Text(level, style=color)


class ScoreTable(Widget):
    """Ranked tool recommendation table with color-coded scores."""

    DEFAULT_CSS = """
    ScoreTable {
        height: 100%;
        width: 100%;
    }
    ScoreTable DataTable {
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        table = DataTable(id="score-table", cursor_type="row")
        table.add_columns("Rank", "Tool", "Score", "Confidence", "Fit")
        yield table

    def load_tools(self, ranked_tools: list[dict]) -> None:
        """Populate the table with scored tool data."""
        try:
            table = self.query_one("#score-table", DataTable)
            table.clear()
            for i, tool in enumerate(ranked_tools, 1):
                score = tool.get("score", 0)
                confidence = tool.get("confidence", "MEDIUM")
                fit_tag = tool.get("fit_tag", "GOOD FIT")
                color = score_color(score)

                rank_text = Text(f"#{i}", style="bold cyan")
                name_text = Text(tool.get("name", "Unknown"), style="bold white")
                score_text = Text(f"{score:.0f}/100", style=color)
                conf_text = confidence_markup(confidence)
                fit_color = FIT_TAGS.get(fit_tag, "white")
                fit_text = Text(fit_tag, style=fit_color)

                table.add_row(rank_text, name_text, score_text, conf_text, fit_text)
        except Exception:
            pass

    def get_selected_tool_name(self) -> str | None:
        """Return the name of the currently selected tool."""
        try:
            table = self.query_one("#score-table", DataTable)
            row_key = table.cursor_row
            cell = table.get_cell_at((row_key, 1))
            return str(cell) if cell else None
        except Exception:
            return None
