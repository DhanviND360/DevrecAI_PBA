"""
DevRecAI CLI — Main Typer application.

Commands:
  devrec run               Launch full interactive TUI session
  devrec history           Browse past recommendation sessions
  devrec export --session  Re-export a past session as Markdown + PDF
  devrec config            Interactive config editor
  devrec feedback          Rate a past session outcome
  devrec train             Retrain the local XGBoost scorer
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

app = typer.Typer(
    name="devrec",
    help="[bold green]DevRecAI[/] — AI-powered DevOps tool recommendation engine",
    rich_markup_mode="rich",
    add_completion=True,
    no_args_is_help=False,
)

console = Console()

ASCII_LOGO_SMALL = r"""
██████╗ ███████╗██╗   ██╗██████╗ ███████╗ ██████╗ █████╗ ██╗
██╔══██╗██╔════╝██║   ██║██╔══██╗██╔════╝██╔════╝██╔══██╗██║
██║  ██║█████╗  ██║   ██║██████╔╝█████╗  ██║     ███████║██║
██║  ██║██╔══╝  ╚██╗ ██╔╝██╔══██╗██╔══╝  ██║     ██╔══██║██║
██████╔╝███████╗ ╚████╔╝ ██║  ██║███████╗╚██████╗██║  ██║██║
╚═════╝ ╚══════╝  ╚═══╝  ╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝
"""


def _print_banner() -> None:
    console.print(
        Panel(
            Text(ASCII_LOGO_SMALL, style="bold green", justify="center"),
            border_style="dark_green",
            subtitle="[dim green]v1.0.0 | AI-powered DevOps tool recommendation[/]",
        )
    )


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """DevRecAI — AI-powered DevOps tool recommendation engine."""
    if ctx.invoked_subcommand is None:
        _print_banner()
        console.print(
            "\n[bold green]▶  Usage:[/] [cyan]devrec run[/]    — launch interactive TUI\n"
            "             [cyan]devrec --help[/] — show all commands\n"
        )


@app.command("run")
def cmd_run(
    skip_boot: bool = typer.Option(False, "--skip-boot", help="Skip the boot animation"),
) -> None:
    """Launch the full interactive TUI session."""
    from devrecai.tui.app import DevRecApp

    tui_app = DevRecApp(skip_boot=skip_boot)
    tui_app.run()


@app.command("history")
def cmd_history() -> None:
    """Browse past recommendation sessions in TUI."""
    from devrecai.tui.app import DevRecApp

    tui_app = DevRecApp(start_screen="history")
    tui_app.run()


@app.command("export")
def cmd_export(
    session: str = typer.Option(..., "--session", "-s", help="Session ID to export"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory"),
) -> None:
    """Re-export a past session as Markdown and PDF."""
    import asyncio

    from devrecai.storage.sessions import SessionManager
    from devrecai.export.markdown import MarkdownExporter
    from devrecai.export.pdf import PDFExporter

    async def _do_export() -> None:
        sm = SessionManager()
        session_data = await sm.get_session(session)
        if not session_data:
            console.print(f"[red]✗ Session not found:[/] {session}")
            raise typer.Exit(1)

        out_dir = Path(output_dir).expanduser() if output_dir else None
        md_exporter = MarkdownExporter()
        pdf_exporter = PDFExporter()

        md_path = await md_exporter.export(session_data, output_dir=out_dir)
        console.print(f"[green]✓ Markdown saved:[/] {md_path}")

        pdf_path = await pdf_exporter.export(session_data, output_dir=out_dir)
        if pdf_path:
            console.print(f"[green]✓ PDF saved:[/] {pdf_path}")
        else:
            console.print("[yellow]⚠ PDF generation skipped (WeasyPrint not available)[/]")

    asyncio.run(_do_export())


@app.command("config")
def cmd_config() -> None:
    """Open the interactive config editor in TUI."""
    from devrecai.tui.app import DevRecApp

    tui_app = DevRecApp(start_screen="config")
    tui_app.run()


@app.command("feedback")
def cmd_feedback(
    session: str = typer.Option(..., "--session", "-s", help="Session ID to rate"),
) -> None:
    """Rate a past session outcome to improve the ML scorer."""
    from devrecai.tui.app import DevRecApp

    tui_app = DevRecApp(start_screen="feedback", session_id=session)
    tui_app.run()


@app.command("train")
def cmd_train(
    min_samples: int = typer.Option(50, "--min-samples", help="Minimum feedback rows before training"),
    force: bool = typer.Option(False, "--force", "-f", help="Force training even with fewer samples"),
) -> None:
    """Retrain the local XGBoost scorer on accumulated feedback data."""
    import asyncio

    from devrecai.engine.ml_scorer import MLScorer
    from devrecai.storage.db import Database

    async def _do_train() -> None:
        console.print("[bold green]DevRecAI ML Trainer[/]\n")
        db = Database()
        await db.init()
        feedback_count = await db.count_feedback()

        if feedback_count < min_samples and not force:
            console.print(
                f"[yellow]⚠ Only {feedback_count} feedback rows collected.[/]\n"
                f"  Need {min_samples} to train. Use [cyan]--force[/] to override.\n"
                f"  Run [cyan]devrec feedback --session <id>[/] to collect more."
            )
            raise typer.Exit(0)

        console.print(f"[green]▶ Starting training on {feedback_count} samples...[/]")
        scorer = MLScorer()
        result = await scorer.train(db=db)

        console.print(f"\n[bold green]✓ Training complete![/]")
        console.print(f"  RMSE: [cyan]{result['rmse']:.4f}[/]")
        console.print(f"  Model saved: [cyan]{result['model_path']}[/]")
        console.print(f"  Samples used: [cyan]{result['sample_count']}[/]")

    asyncio.run(_do_train())


if __name__ == "__main__":
    app()
