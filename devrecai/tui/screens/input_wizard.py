"""
DevRecAI Input Wizard Screen.

5-step multi-screen form to collect project requirements.
Each step properly mounts its field widgets via async mount.
"""
from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Input, Label, Select, Static, TextArea
from textual.containers import Horizontal, Vertical, ScrollableContainer

# ─── Step Definitions ─────────────────────────────────────────────────────────

STEPS = [
    {
        "title": "PROJECT BASICS",
        "fields": [
            {"name": "project_name", "type": "text", "label": "Project Name", "required": True},
            {
                "name": "project_type",
                "type": "select",
                "label": "Project Type",
                "options": [
                    ("Greenfield", "greenfield"),
                    ("Migration", "migration"),
                    ("Scaling existing", "scaling"),
                    ("Modernisation", "modernisation"),
                    ("Disaster recovery", "disaster_recovery"),
                ],
            },
            {
                "name": "description",
                "type": "textarea",
                "label": "Brief Description (2-3 sentences)",
                "required": True,
            },
        ],
    },
    {
        "title": "TEAM PROFILE",
        "fields": [
            {
                "name": "team_size",
                "type": "select",
                "label": "Team Size",
                "options": [
                    ("Solo (1)", "solo"),
                    ("Small (2-10)", "small"),
                    ("Mid (11-50)", "mid"),
                    ("Large (51-200)", "large"),
                    ("Enterprise (200+)", "enterprise"),
                ],
            },
            {
                "name": "devops_maturity",
                "type": "select",
                "label": "DevOps Maturity",
                "options": [
                    ("Beginner", "beginner"),
                    ("Intermediate", "intermediate"),
                    ("Advanced", "advanced"),
                    ("SRE-level", "sre"),
                ],
            },
            {
                "name": "budget_tier",
                "type": "select",
                "label": "Tooling Budget",
                "options": [
                    ("Open-source only", "oss"),
                    ("Low (<$500/mo)", "low"),
                    ("Medium ($500-5k/mo)", "medium"),
                    ("Enterprise (unlimited)", "enterprise"),
                ],
            },
        ],
    },
    {
        "title": "TECHNOLOGY STACK",
        "fields": [
            {
                "name": "languages",
                "type": "multicheck",
                "label": "Primary Languages",
                "options": ["Python", "Go", "Java", "Node.js", "Ruby", "Rust", ".NET", "PHP", "Other"],
            },
            {
                "name": "cloud_provider",
                "type": "multicheck",
                "label": "Cloud Provider(s)",
                "options": ["AWS", "GCP", "Azure", "On-premise", "Hybrid", "Multi-cloud"],
            },
            {
                "name": "existing_tools",
                "type": "text",
                "label": "Existing tools in use (comma-separated, optional)",
                "required": False,
            },
        ],
    },
    {
        "title": "REQUIREMENTS & PAIN POINTS",
        "fields": [
            {
                "name": "priorities",
                "type": "multicheck",
                "label": "Top Priorities (select all that apply)",
                "options": [
                    "CI/CD speed",
                    "Security & compliance",
                    "Observability",
                    "Cost optimisation",
                    "Developer experience",
                    "Scalability",
                    "Reliability",
                ],
            },
            {
                "name": "pain_points",
                "type": "textarea",
                "label": "Describe your current pain points",
                "required": True,
            },
            {
                "name": "compliance",
                "type": "multicheck",
                "label": "Compliance Requirements",
                "options": ["None", "SOC2", "HIPAA", "GDPR", "PCI-DSS", "ISO27001", "FedRAMP"],
            },
        ],
    },
    {
        "title": "DEPLOYMENT & INFRASTRUCTURE",
        "fields": [
            {
                "name": "deployment_style",
                "type": "select",
                "label": "Deployment Style",
                "options": [
                    ("Containers (Kubernetes)", "kubernetes"),
                    ("Containers (ECS/Nomad)", "ecs"),
                    ("Serverless", "serverless"),
                    ("VMs", "vms"),
                    ("Bare metal", "bare_metal"),
                    ("Hybrid", "hybrid"),
                ],
            },
            {
                "name": "deployment_frequency",
                "type": "select",
                "label": "Desired Deployment Frequency",
                "options": [
                    ("Multiple times/day", "many_per_day"),
                    ("Daily", "daily"),
                    ("Weekly", "weekly"),
                    ("Monthly", "monthly"),
                    ("On demand", "on_demand"),
                ],
            },
            {
                "name": "uptime_requirement",
                "type": "select",
                "label": "Uptime SLA Target",
                "options": [
                    ("99% (7.3 hrs/mo downtime ok)", "99"),
                    ("99.9% (44 min/mo)", "99.9"),
                    ("99.95% (22 min/mo)", "99.95"),
                    ("99.99% (4.4 min/mo)", "99.99"),
                    ("99.999% (26 sec/mo)", "99.999"),
                ],
            },
        ],
    },
]


def _field_key(opt: str) -> str:
    """Normalise an option string to a safe widget ID suffix."""
    return opt.replace(" ", "_").replace("/", "_").replace("&", "and").replace(".", "").replace("-", "_").lower()


class InputWizardScreen(Screen):
    """5-step project requirements wizard."""

    BINDINGS = [
        Binding("ctrl+n", "next_step", "Next"),
        Binding("ctrl+b", "prev_step", "Back"),
        Binding("escape", "save_exit", "Save & Exit"),
        Binding("n", "next_step", "Next", show=False),
        Binding("b", "prev_step", "Back", show=False),
    ]

    CSS = """
    InputWizardScreen {
        background: #0A0A0A;
        align: center top;
        padding: 1;
    }

    #wizard-container {
        width: 90;
        height: 90%;
        border: double #003B00;
        padding: 1 3;
    }

    #step-header {
        color: #00CFFF;
        text-style: bold;
        width: 100%;
        text-align: center;
        margin-bottom: 0;
        height: 1;
    }

    #progress-label {
        color: #005F00;
        width: 100%;
        text-align: center;
        margin-bottom: 1;
        height: 1;
    }

    #fields-scroll {
        width: 100%;
        height: 1fr;
        overflow-y: auto;
    }

    #fields-inner {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    .field-label {
        color: #00FF41;
        margin-top: 1;
        height: 1;
    }

    Input {
        width: 100%;
        margin: 0 0 1 0;
    }

    Select {
        width: 100%;
        margin: 0 0 1 0;
    }

    TextArea {
        width: 100%;
        height: 5;
        margin: 0 0 1 0;
    }

    .check-row {
        layout: horizontal;
        width: 100%;
        height: auto;
    }

    Checkbox {
        color: #00FF41;
        background: transparent;
        width: 30;
    }

    #nav-bar {
        layout: horizontal;
        width: 100%;
        margin-top: 1;
        height: 3;
        align: center middle;
    }

    Button {
        width: 20;
    }

    #validation-msg {
        color: #FF3131;
        width: 100%;
        text-align: center;
        height: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._step = 0
        self._data: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard-container"):
            yield Static("", id="step-header")
            yield Static("", id="progress-label")
            with ScrollableContainer(id="fields-scroll"):
                yield Vertical(id="fields-inner")
            yield Static("", id="validation-msg")
            with Horizontal(id="nav-bar"):
                yield Button("◀ Back [B]", id="btn-back", variant="default")
                yield Button("Next [N] ▶", id="btn-next", variant="success")

    def on_mount(self) -> None:
        self._render_step()

    # ─── Rendering ────────────────────────────────────────────────────────────

    def _render_step(self) -> None:
        step = STEPS[self._step]
        total = len(STEPS)
        n = self._step + 1

        bar = "█" * n + "░" * (total - n)
        self.query_one("#step-header", Static).update(
            f"STEP {n} OF {total} — {step['title']}  [{bar}]"
        )
        self.query_one("#progress-label", Static).update(
            "Use [N] Next / [B] Back / [Esc] Save & Exit"
        )
        self.query_one("#btn-back", Button).disabled = self._step == 0
        self.query_one("#btn-next", Button).label = (
            "Finish ✓" if self._step == total - 1 else "Next [N] ▶"
        )
        self.query_one("#validation-msg", Static).update("")

        # Rebuild the fields area
        inner = self.query_one("#fields-inner", Vertical)
        inner.remove_children()
        self.call_after_refresh(self._mount_step_fields, step["fields"])

    def _mount_step_fields(self, fields: list[dict]) -> None:
        """Mount widget children for the current step into #fields-inner."""
        inner = self.query_one("#fields-inner", Vertical)
        widgets_to_add: list = []

        for field in fields:
            name = field["name"]
            label_text = field["label"]
            req = " *" if field.get("required") else ""
            widgets_to_add.append(Label(f"{label_text}{req}", classes="field-label"))

            ftype = field["type"]
            if ftype == "text":
                widgets_to_add.append(Input(placeholder=label_text, id=f"field-{name}"))
            elif ftype == "textarea":
                widgets_to_add.append(TextArea(id=f"field-{name}"))
            elif ftype == "select":
                opts = field.get("options", [])
                # Ensure options is a list of (label, value) tuples
                select_opts = [(o[0], o[1]) if isinstance(o, (tuple, list)) else (o, o) for o in opts]
                widgets_to_add.append(
                    Select(select_opts, value=select_opts[0][1] if select_opts else None, id=f"field-{name}")
                )
            elif ftype == "multicheck":
                opts = field.get("options", [])
                # Lay out in rows of 3
                row_widgets: list = []
                for i, opt in enumerate(opts):
                    key = _field_key(opt)
                    row_widgets.append(Checkbox(opt, id=f"cb-{name}-{key}"))
                    if len(row_widgets) == 3 or i == len(opts) - 1:
                        widgets_to_add.append(Horizontal(*row_widgets, classes="check-row"))
                        row_widgets = []

        for w in widgets_to_add:
            inner.mount(w)

    # ─── Data Collection ──────────────────────────────────────────────────────

    def _collect_and_validate(self) -> tuple[dict, list[str]]:
        """Collect current step field values. Returns (values, errors)."""
        step = STEPS[self._step]
        values: dict = {}
        errors: list[str] = []

        for field in step["fields"]:
            name = field["name"]
            ftype = field["type"]
            try:
                if ftype == "text":
                    widget = self.query_one(f"#field-{name}", Input)
                    values[name] = widget.value.strip()
                    if field.get("required") and not values[name]:
                        errors.append(f"{field['label']} is required")
                elif ftype == "textarea":
                    widget = self.query_one(f"#field-{name}", TextArea)
                    values[name] = widget.text.strip()
                    if field.get("required") and not values[name]:
                        errors.append(f"{field['label']} is required")
                elif ftype == "select":
                    widget = self.query_one(f"#field-{name}", Select)
                    val = widget.value
                    values[name] = str(val) if val != Select.BLANK else ""
                elif ftype == "multicheck":
                    selected = []
                    for opt in field["options"]:
                        key = _field_key(opt)
                        try:
                            cb = self.query_one(f"#cb-{name}-{key}", Checkbox)
                            if cb.value:
                                selected.append(opt)
                        except Exception:
                            pass
                    values[name] = selected
            except Exception:
                values[name] = "" if field["type"] != "multicheck" else []

        return values, errors

    # ─── Actions ──────────────────────────────────────────────────────────────

    def action_next_step(self) -> None:
        self._advance()

    def action_prev_step(self) -> None:
        if self._step > 0:
            self._step -= 1
            self._render_step()

    def action_save_exit(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            self._advance()
        elif event.button.id == "btn-back":
            self.action_prev_step()

    def _advance(self) -> None:
        values, errors = self._collect_and_validate()
        if errors:
            self.query_one("#validation-msg", Static).update(f"✗ {errors[0]}")
            return

        self._data.update(values)
        self.query_one("#validation-msg", Static).update("")

        if self._step >= len(STEPS) - 1:
            # All steps complete — launch processing
            profile = dict(self._data)
            self.app.switch_screen_with_processing(profile)
        else:
            self._step += 1
            self._render_step()
