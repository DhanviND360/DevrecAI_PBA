"""
DevRecAI Export Screen.

Animated report generation with progress display.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Label, Static
from textual.containers import Vertical


class ExportScreen(Screen):
    """Animated export progress screen."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("q", "go_back", "Back"),
    ]

    CSS = """
    ExportScreen {
        align: center middle;
        background: #0A0A0A;
    }

    #export-container {
        width: 70;
        height: auto;
        border: double #003B00;
        padding: 2 4;
    }

    #export-title {
        color: #00FF41;
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    .export-row {
        color: #00CFFF;
        width: 100%;
        margin: 0 0 1 0;
    }

    .export-row.done {
        color: #39FF14;
    }

    .export-row.error {
        color: #FF3131;
    }

    #save-path {
        color: #005F00;
        width: 100%;
        margin-top: 1;
    }

    #btn-back {
        margin-top: 2;
    }
    """

    def __init__(self, profile: dict, results: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self._profile = profile
        self._results = results

    def compose(self) -> ComposeResult:
        with Vertical(id="export-container"):
            yield Static("[ EXPORTING REPORT ]", id="export-title")
            yield Static("Writing Markdown report...    ░░░░░░░░░░", id="md-row", classes="export-row")
            yield Static("Generating PDF...             ░░░░░░░░░░", id="pdf-row", classes="export-row")
            yield Static("", id="save-path")
            yield Button("Done — Press Q to go back", id="btn-back")

    def on_mount(self) -> None:
        self.query_one("#btn-back", Button).display = False
        self.call_after_refresh(self._do_export)

    async def _do_export(self) -> None:
        try:
            from devrecai.export.markdown import MarkdownExporter
            from devrecai.export.pdf import PDFExporter

            # Markdown
            self.query_one("#md-row", Static).update(
                "Writing Markdown report...    [████████░░] 80%"
            )
            md_exp = MarkdownExporter()
            md_path = await md_exp.export(
                {"profile_json": self._profile, "results_json": self._results}
            )
            self.query_one("#md-row", Static).update(
                f"Writing Markdown report...    [██████████] DONE ✓"
            )
            self.query_one("#md-row", Static).set_classes("export-row done")

            # PDF
            self.query_one("#pdf-row", Static).update(
                "Generating PDF...             [████████░░] 80%"
            )
            pdf_exp = PDFExporter()
            pdf_path = await pdf_exp.export(
                {"profile_json": self._profile, "results_json": self._results}
            )
            if pdf_path:
                self.query_one("#pdf-row", Static).update(
                    "Generating PDF...             [██████████] DONE ✓"
                )
                self.query_one("#pdf-row", Static).set_classes("export-row done")
            else:
                self.query_one("#pdf-row", Static).update(
                    "Generating PDF...             SKIPPED (WeasyPrint not installed)"
                )

            # Show save path
            parent = Path(md_path).parent if md_path else "~/devrec-reports/"
            self.query_one("#save-path", Static).update(
                f"Files saved to: {parent}"
            )

        except Exception as e:
            self.query_one("#save-path", Static).update(f"Export error: {e}")

        self.query_one("#btn-back", Button).display = True

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.action_go_back()
