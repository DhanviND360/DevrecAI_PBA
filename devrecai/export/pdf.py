"""
DevRecAI PDF Generator.

Converts Markdown reports to PDF using WeasyPrint (preferred)
or falls back to ReportLab. Applies retro terminal dark-theme CSS.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from devrecai.config.settings import get_settings

logger = logging.getLogger(__name__)

RETRO_CSS = """
@page {
    margin: 1.5cm;
    size: A4;
}

body {
    background: #0A0A0A;
    color: #00FF41;
    font-family: "Courier New", Courier, monospace;
    font-size: 10pt;
    line-height: 1.6;
}

h1, h2, h3 {
    color: #39FF14;
    border-bottom: 1px solid #003B00;
    padding-bottom: 4px;
}

h1 { font-size: 16pt; }
h2 { font-size: 14pt; }
h3 { font-size: 12pt; color: #00CFFF; }

table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
}

th {
    background: #003B00;
    color: #39FF14;
    padding: 6px 10px;
    text-align: left;
    font-weight: bold;
}

td {
    padding: 5px 10px;
    border-bottom: 1px solid #001A00;
}

tr:nth-child(even) td {
    background: #0D0D0D;
}

code, pre {
    background: #111111;
    color: #00CFFF;
    padding: 2px 6px;
    border: 1px solid #003B00;
    border-radius: 2px;
}

pre {
    padding: 10px;
    overflow: auto;
}

blockquote {
    border-left: 3px solid #00FF41;
    color: #005F00;
    padding-left: 12px;
    margin-left: 0;
}

a { color: #00CFFF; }

strong { color: #39FF14; }
em { color: #FFD700; }
"""


class PDFExporter:
    """WeasyPrint PDF generation from Markdown reports."""

    def __init__(self) -> None:
        self._settings = get_settings()

    async def export(
        self,
        session_data: dict,
        output_dir: Optional[Path] = None,
        markdown_content: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate a PDF report from session data.
        Returns path to PDF file, or None if WeasyPrint unavailable.
        """
        # Generate markdown if not provided
        if not markdown_content:
            from devrecai.export.markdown import MarkdownExporter
            md_exp = MarkdownExporter()
            md_path = await md_exp.export(session_data, output_dir=output_dir)
            with open(md_path) as f:
                markdown_content = f.read()

        # Determine output path
        if output_dir is None:
            output_dir = Path(self._settings.output.directory).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)

        profile = session_data.get("profile_json", {})
        project_name = profile.get("project_name", "report")
        date_str = datetime.now().strftime("%Y-%m-%d")
        slug = project_name.lower().replace(" ", "_").replace("/", "-")
        filename = f"{date_str}_{slug}_DevRecAI_Report.pdf"
        filepath = output_dir / filename

        html_content = self._markdown_to_html(markdown_content)

        # Try WeasyPrint first
        try:
            return self._render_weasyprint(html_content, filepath)
        except ImportError:
            logger.warning("WeasyPrint not installed — trying ReportLab fallback.")
        except Exception as e:
            logger.warning(f"WeasyPrint error: {e}")

        # Try ReportLab fallback
        try:
            return self._render_reportlab(markdown_content, filepath)
        except ImportError:
            logger.warning("ReportLab not installed either — PDF generation skipped.")
        except Exception as e:
            logger.warning(f"ReportLab error: {e}")

        return None

    def _markdown_to_html(self, md: str) -> str:
        """Convert Markdown to HTML with retro CSS styling."""
        try:
            import markdown
            body = markdown.markdown(md, extensions=["tables", "fenced_code"])
        except ImportError:
            # Simple fallback: wrap in pre
            body = f"<pre>{md}</pre>"

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>DevRecAI Report</title>
<style>
{RETRO_CSS}
</style>
</head>
<body>
{body}
</body>
</html>"""

    def _render_weasyprint(self, html: str, filepath: Path) -> str:
        from weasyprint import HTML, CSS
        HTML(string=html).write_pdf(str(filepath))
        return str(filepath)

    def _render_reportlab(self, md: str, filepath: Path) -> str:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        doc = SimpleDocTemplate(str(filepath), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        for line in md.split("\n"):
            if line.startswith("# "):
                story.append(Paragraph(line[2:], styles["h1"]))
            elif line.startswith("## "):
                story.append(Paragraph(line[3:], styles["h2"]))
            elif line.startswith("### "):
                story.append(Paragraph(line[4:], styles["h3"]))
            elif line.strip():
                story.append(Paragraph(line, styles["Normal"]))
            else:
                story.append(Spacer(1, 6))

        doc.build(story)
        return str(filepath)
