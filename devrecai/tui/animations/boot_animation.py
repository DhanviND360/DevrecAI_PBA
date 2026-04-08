"""
DevRecAI Boot Animation Helpers.

Generates retro BIOS-style POST lines populated with REAL system specs
(CPU, RAM, OS, Python version, disk), ASCII art, scanline shimmer,
and progress bar frames for the boot screen.
"""
from __future__ import annotations

import os
import platform
import random
import sys
from datetime import datetime
from pathlib import Path

# ─── Live System Specs ────────────────────────────────────────────────────────

def _cpu_info() -> str:
    """Return a formatted CPU info string."""
    cpu = platform.processor() or platform.machine() or "Unknown CPU"
    try:
        import psutil
        freq = psutil.cpu_freq()
        cores = psutil.cpu_count(logical=False) or 1
        threads = psutil.cpu_count(logical=True) or 1
        freq_str = f"@ {freq.max / 1000:.2f}GHz" if freq and freq.max else ""
        return f"{cpu} {freq_str}  [{cores}C/{threads}T]"
    except Exception:
        cores = os.cpu_count() or 1
        return f"{cpu}  [{cores} cores]"


def _ram_info() -> str:
    """Return total and available RAM."""
    try:
        import psutil
        vm = psutil.virtual_memory()
        total_gb = vm.total / (1024 ** 3)
        avail_gb = vm.available / (1024 ** 3)
        return f"{total_gb:.1f} GB total, {avail_gb:.1f} GB free"
    except Exception:
        return "N/A"


def _disk_info() -> str:
    """Return disk usage for the project drive."""
    try:
        import psutil
        disk = psutil.disk_usage(str(Path.home()))
        total_gb = disk.total / (1024 ** 3)
        free_gb  = disk.free  / (1024 ** 3)
        return f"{total_gb:.0f} GB total, {free_gb:.1f} GB free"
    except Exception:
        return "N/A"


def _gpu_info() -> str:
    """Return GPU name if detectable, else graceful fallback."""
    # Try nvidia-smi path
    try:
        import subprocess
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).decode().strip().splitlines()
        if out and out[0]:
            return out[0]
    except Exception:
        pass
    # Try wmic on Windows
    if platform.system() == "Windows":
        try:
            import subprocess
            out = subprocess.check_output(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                stderr=subprocess.DEVNULL,
                timeout=2,
            ).decode().strip().splitlines()
            names = [ln.strip() for ln in out if ln.strip() and ln.strip() != "Name"]
            if names:
                return names[0]
        except Exception:
            pass
    return "Integrated / Not detected"


def _os_info() -> str:
    """Return OS name + version."""
    system = platform.system()
    if system == "Windows":
        return f"Windows {platform.version().split('.')[0]} (build {platform.version()})"
    elif system == "Darwin":
        return f"macOS {platform.mac_ver()[0]}"
    else:
        return f"{system} {platform.release()}"


def _python_info() -> str:
    return f"Python {sys.version.split()[0]}  [{platform.architecture()[0]}]"


def _llm_provider() -> str:
    """Detect configured LLM provider from env."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "Anthropic Claude  [KEY FOUND]"
    if os.environ.get("OPENAI_API_KEY"):
        return "OpenAI GPT  [KEY FOUND]"
    return "No API key set  [OFFLINE MODE]"


def _tool_count() -> str:
    """Count tools in tools.json."""
    try:
        from devrecai.engine.tools_db import load_tools
        return str(len(load_tools()))
    except Exception:
        return "?"


def _model_status() -> str:
    """Check if a trained ML model exists."""
    from devrecai.config.settings import DEVREC_DIR
    model_path = DEVREC_DIR / "models" / "latest.json"
    if model_path.exists():
        mtime = datetime.fromtimestamp(model_path.stat().st_mtime)
        return f"XGBoost model found  (trained {mtime.strftime('%Y-%m-%d')})"
    return "XGBoost  [No model — run: devrec train]"


def _db_status() -> str:
    """Check if DuckDB session file exists."""
    from devrecai.config.settings import DEVREC_DIR
    db_path = DEVREC_DIR / "sessions.db"
    if db_path.exists():
        size_kb = db_path.stat().st_size / 1024
        return f"DuckDB sessions.db  ({size_kb:.0f} KB)  [OK]"
    return "DuckDB  [No session history yet]  [OK]"


# Build the POST lines once at import time so the screen renders instantly
def _build_post_lines() -> list[str]:
    return [
        f"DevRecAI BIOS v2.11.0  Copyright (C) {datetime.now().year} DevRecAI Systems",
        "─" * 60,
        f"OS:   {_os_info()}",
        f"CPU:  {_cpu_info()}",
        f"RAM:  {_ram_info()}",
        f"GPU:  {_gpu_info()}",
        f"DISK: {_disk_info()}",
        f"PY:   {_python_info()}",
        "─" * 60,
        f"LLM provider.......... {_llm_provider()}",
        f"Tool database......... {_tool_count()} DevOps tools indexed  [OK]",
        f"ML scorer............. {_model_status()}",
        f"Session store......... {_db_status()}",
        f"Rule engine........... 8-criterion weighted scorer  [LOADED]",
        f"Offline mode.......... Available  [OK]",
        "─" * 60,
        "",
        "Initialising DevRecAI...",
    ]


# Populated lazily on first access so we don't slow CLI startup
_POST_LINES_CACHE: list[str] | None = None


def get_post_lines() -> list[str]:
    """Return (and cache) real POST lines with live system specs."""
    global _POST_LINES_CACHE
    if _POST_LINES_CACHE is None:
        _POST_LINES_CACHE = _build_post_lines()
    return _POST_LINES_CACHE


# Keep POST_LINES as a module-level alias for backwards compatibility
POST_LINES: list[str] = []   # filled on first call to get_post_lines()


# ─── ASCII Boot Logo ──────────────────────────────────────────────────────────

BOOT_LOGO = r"""
  ██████╗ ███████╗██╗   ██╗██████╗ ███████╗ ██████╗ █████╗ ██╗
  ██╔══██╗██╔════╝██║   ██║██╔══██╗██╔════╝██╔════╝██╔══██╗██║
  ██║  ██║█████╗  ██║   ██║██████╔╝█████╗  ██║     ███████║██║
  ██║  ██║██╔══╝  ╚██╗ ██╔╝██╔══██╗██╔══╝  ██║     ██╔══██║██║
  ██████╔╝███████╗ ╚████╔╝ ██║  ██║███████╗╚██████╗██║  ██║██║
  ╚═════╝ ╚══════╝  ╚═══╝  ╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝
"""


# ─── Progress messages ────────────────────────────────────────────────────────

PROGRESS_MESSAGES = [
    "Loading recommendation engine",
    "Indexing DevOps tool database",
    "Warming up ML scorer",
    "Calibrating rule weights",
    "Connecting to LLM provider",
    "Verifying configuration",
    "Scanning session history",
    "Ready",
]


# ─── Retro tips ───────────────────────────────────────────────────────────────

RETRO_TIPS = [
    "DID YOU KNOW: ArgoCD GitOps adoption grew 340% in 2023 (CNCF Survey)",
    "DID YOU KNOW: 83% of high-performing teams use trunk-based development (DORA 2023)",
    "DID YOU KNOW: Kubernetes powers 96% of Fortune 500 container workloads",
    "DID YOU KNOW: Mean time to restore (MTTR) under 1 hour is an elite DevOps KPI",
    "DID YOU KNOW: Terraform has 40k+ GitHub stars and 3,000+ provider plugins",
    "DID YOU KNOW: Teams using GitOps deploy 2.5x more frequently (Weaveworks Report)",
    "DID YOU KNOW: Vault by HashiCorp is the #1 secrets management choice in enterprises",
    "DID YOU KNOW: Observability reduces MTTR by 60% vs. traditional monitoring",
    "DID YOU KNOW: eBPF-based tools like Falco detect runtime threats with <1% overhead",
    "DID YOU KNOW: GitHub Actions is used by 90M+ developers worldwide",
    "DID YOU KNOW: Grafana has become the de-facto standard for metrics dashboards",
    "DID YOU KNOW: Multi-cloud adoption increased to 87% in 2024 (Flexera Report)",
]


def get_random_tip() -> str:
    return random.choice(RETRO_TIPS)


# ─── Animation helpers ────────────────────────────────────────────────────────

def build_progress_bar(percent: int, width: int = 40) -> str:
    filled = int(width * percent / 100)
    empty  = width - filled
    return f"[{'█' * filled}{'░' * empty}] {percent}%"


def build_scanline_logo(frame: int = 0) -> str:
    lines  = BOOT_LOGO.split("\n")
    result = []
    for i, line in enumerate(lines):
        if (i + frame) % 4 == 0:
            result.append(f"[bold bright_green]{line}[/]")
        elif (i + frame) % 4 == 2:
            result.append(f"[green]{line}[/]")
        else:
            result.append(f"[bright_green]{line}[/]")
    return "\n".join(result)


SPINNER_FRAMES = ["|", "/", "—", "\\"]


def get_spinner_frame(tick: int) -> str:
    return SPINNER_FRAMES[tick % len(SPINNER_FRAMES)]
