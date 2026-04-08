# DevRecAI

> **AI-powered DevOps tool recommendation engine — terminal native, privacy first.**

```
 ██████╗ ███████╗██╗   ██╗██████╗ ███████╗ ██████╗ █████╗ ██╗
 ██╔══██╗██╔════╝██║   ██║██╔══██╗██╔════╝██╔════╝██╔══██╗██║
 ██║  ██║█████╗  ██║   ██║██████╔╝█████╗  ██║     ███████║██║
 ██║  ██║██╔══╝  ╚██╗ ██╔╝██╔══██╗██╔══╝  ██║     ██╔══██║██║
 ██████╔╝███████╗ ╚████╔╝ ██║  ██║███████╗╚██████╗██║  ██║██║
 ╚═════╝ ╚══════╝  ╚═══╝  ╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝
```

DevRecAI is a terminal-native, AI-powered tool recommendation engine for DevOps engineers,
platform teams, and engineering leaders. It evaluates 33+ DevOps tools across 14 categories
against your specific project profile and generates ranked, explainable recommendations —
powered by LLMs and an XGBoost scorer trained on real-world feedback.

---

## Features

- 🖥️ **Retro terminal TUI** — BIOS-style boot animation, ASCII art, scanline effects
- 🤖 **LLM explanations** — Anthropic Claude or OpenAI GPT-powered justifications
- 📊 **Dual scoring** — Rule-based deterministic scorer + XGBoost ML model (hybrid mode)
- 🗃️ **33+ tools** across 14 categories: CI/CD, Observability, Security, IaC, Orchestration, and more
- 📋 **Professional reports** — Markdown + PDF export with full toolchain justifications
- 💾 **Session history** — DuckDB-backed persistent sessions with re-export capability
- 🔁 **Feedback loop** — Rate past sessions to improve the ML scorer over time
- 🔒 **Privacy first** — All data stays local, no cloud telemetry

---

## Installation

### Requirements

- Python 3.11+
- pip

### Install

```bash
# Clone the repository
git clone <repo-url>
cd DevRecAI

# Install the package (creates the devrec CLI command)
pip install -e .

# Optional: install dev dependencies
pip install -e ".[dev]"
```

### Verify Installation

```bash
devrec --help
```

---

## Usage

### Launch interactive TUI

```bash
devrec run
```

This launches the full interactive session:
1. **Boot screen** — Retro BIOS animation (press any key to skip)
2. **Home menu** — Navigate with arrow keys or `1-4`
3. **Input wizard** — 5-step form: project basics, team, stack, requirements, deployment
4. **Processing** — LLM + scorer runs in the background
5. **Results screen** — Category tabs with ranked tools, AI explanation panel
6. **Export** — Markdown + PDF report saved to `~/devrec-reports/`

### Browse history

```bash
devrec history
```

### Re-export a session

```bash
devrec export --session <session-id>
```

### Configure LLM provider

```bash
devrec config
```

Or set environment variables:
```bash
export ANTHROPIC_API_KEY=sk-ant-...   # Default provider
export OPENAI_API_KEY=sk-...          # For OpenAI
```

### Submit feedback (improves ML scorer)

```bash
devrec feedback --session <session-id>
```

### Retrain the ML scorer

```bash
# After collecting 50+ feedback entries:
devrec train

# Force training with fewer samples:
devrec train --force
```

---

## Configuration

Config file: `~/.devrec/config.yaml`

```yaml
llm:
  provider: anthropic          # anthropic | openai | custom
  model: claude-sonnet-4-20250514
  api_key_env: ANTHROPIC_API_KEY
  timeout_seconds: 60
  streaming: true

scorer:
  mode: hybrid                 # hybrid | rule_based | ml_model
  confidence_threshold: 0.7

output:
  directory: ~/devrec-reports/
  formats: [markdown, pdf]

theme:
  name: retro-green            # retro-green | amber | ice-blue | ghost-white
  animations: true
  boot_sequence: true
```

---

## Tool Categories

DevRecAI evaluates tools across 14 categories:

| Category | Example Tools |
|----------|--------------|
| CI/CD | GitHub Actions, GitLab CI, Jenkins, Tekton |
| Observability & Monitoring | Prometheus, Grafana, Datadog, New Relic |
| Security & Compliance | Trivy, Falco, Snyk |
| Infrastructure as Code | Terraform, Pulumi, Ansible, Helm |
| Container Orchestration | Kubernetes, Amazon ECS, Nomad |
| Artifact Registry | Harbor, Amazon ECR |
| Secrets Management | Vault, AWS Secrets Manager |
| Service Mesh | Istio, Linkerd |
| GitOps | ArgoCD, Flux |
| Testing & QA | SonarQube |
| Incident Management | PagerDuty, OpsGenie |
| Cost Management | Infracost, OpenCost |
| API Gateway | Kong |
| Log Management | Elasticsearch / Loki |

---

## Scoring System

### Hybrid Mode (Default)

DevRecAI uses three scoring modes:

- **Rule-based** — Deterministic weighted scoring, always available offline
  - Weights: stack compatibility (25%), team fit (15%), budget (15%), compliance (15%), community health (10%), learning curve (10%), lock-in risk (5%), integration breadth (5%)
- **ML Model** — XGBoost trained on real-world feedback (available after `devrec train`)
- **Hybrid** — Uses ML score if confidence > 0.7, otherwise blends 50/50 with rule-based

### Feedback Loop

1. Use DevRecAI and run `devrec feedback` to rate how tools performed
2. After 50+ ratings, run `devrec train` to retrain the XGBoost model
3. ML predictions improve progressively with more feedback data

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Lint
ruff check .

# Type check
mypy devrecai/

# Run TUI in dev mode (Textual console)
textual run --dev devrecai/tui/app.py
```

---

## Project Structure

```
DevRecAI/
├── devrecai/
│   ├── cli/          # Typer CLI commands
│   ├── tui/          # Textual TUI screens, widgets, animations
│   │   ├── screens/  # boot, home, wizard, processing, results, history, config, feedback, export, comparison
│   │   ├── widgets/  # retro_progress, spinner, score_table
│   │   └── animations/  # boot_animation
│   ├── engine/       # scorer, rules, ml_scorer, tools_db
│   ├── llm/          # client, prompts, explainer
│   ├── storage/      # db (DuckDB), sessions
│   ├── export/       # markdown, pdf
│   ├── config/       # settings (Pydantic)
│   └── data/
│       ├── tools.json         # 33+ DevOps tools knowledge base
│       ├── training/          # Training datasets
│       └── model/             # XGBoost model artifacts
├── tests/
│   ├── test_scorer.py
│   ├── test_llm_client.py
│   └── test_storage.py
├── pyproject.toml
└── README.md
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*DevRecAI v1.0.0 | Python 3.11+ | Powered by Textual + Anthropic/OpenAI + XGBoost*
