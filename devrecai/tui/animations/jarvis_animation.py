"""
DevRecAI JARVIS Animation Screen.

Cyberpunk/JARVIS-style radial animation displayed between the
Home screen and the Input Wizard:
- Concentric pulsing circles (ASCII art rendered per frame)
- Rotating arc segments in cyan/blue
- Scanning sweep line
- Telemetry read-out lines in corner HUDs
- "INITIALIZING ANALYSIS ENGINE" center text
- Auto-advances after ~3 s or any key press
"""
from __future__ import annotations

import asyncio
import math
import random
import time
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static

# ── Unicode / ASCII drawing primitives ──────────────────────────────────────

# Characters used to draw concentric rings at different pseudo-distances
_RING_CHARS: list[str] = ["·", "∘", "○", "◎", "◉", "⊙", "●"]

# Braille-style block characters for dense fills
_ARC_CHARS = "·⠂⠃⠇⡇⣇⣏⣟⣿"

# Column widths of the terminal canvas
_W = 78
_H = 24

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _build_frame(tick: int) -> str:
    """
    Render one animation frame as a plain string (_W × _H characters).
    Uses pure math — no external deps.
    """
    t = tick * 0.12  # time factor

    # Centre of canvas (terminal chars are ~2:1 tall, compensate with x*0.45)
    cx = _W / 2
    cy = _H / 2

    # Build a grid of characters
    grid: list[list[str]] = [[" "] * _W for _ in range(_H)]

    # ── 1. Concentric rings ────────────────────────────────────────────────
    radii = [3, 6, 9, 13, 17, 21]
    for ri, r in enumerate(radii):
        # Each ring pulses slightly
        pulse = 0.4 * math.sin(t * 1.8 + ri * 0.9)
        effective_r = r + pulse
        # Walk around the circle
        steps = max(60, int(effective_r * 12))
        for s in range(steps):
            angle = (2 * math.pi * s) / steps
            # Draw gaps on some rings for arc effect
            gap_start = (t * 0.8 + ri * 1.1) % (2 * math.pi)
            gap_size = 0.3 + 0.15 * math.sin(t + ri)
            gap_end = gap_start + gap_size
            if gap_start < angle < gap_end or (gap_end > 2 * math.pi and angle < gap_end - 2 * math.pi):
                continue  # gap in arc
            # Map to grid coords (compress x so circles look round)
            px = int(cx + effective_r * math.cos(angle) * 2.1)
            py = int(cy + effective_r * math.sin(angle))
            if 0 <= px < _W and 0 <= py < _H:
                # Brighter char for closer rings
                c = _RING_CHARS[min(ri, len(_RING_CHARS) - 1)]
                grid[py][px] = c

    # ── 2. Rotating dashed crosshairs ─────────────────────────────────────
    for arm in range(4):
        arm_angle = t * 0.6 + arm * (math.pi / 2)
        for d in range(1, 25):
            px = int(cx + d * math.cos(arm_angle) * 2.1)
            py = int(cy + d * math.sin(arm_angle))
            if 0 <= px < _W and 0 <= py < _H:
                if d % 3 != 0:  # dashed
                    grid[py][px] = "─" if abs(math.cos(arm_angle)) > 0.7 else "│"

    # ── 3. Sweeping scan line ──────────────────────────────────────────────
    sweep_angle = (t * 1.4) % (2 * math.pi)
    for d in range(1, 22):
        px = int(cx + d * math.cos(sweep_angle) * 2.1)
        py = int(cy + d * math.sin(sweep_angle))
        if 0 <= px < _W and 0 <= py < _H:
            grid[py][px] = "█"
        # Fading trail (3 ghost lines)
        for ghost in range(1, 4):
            ga = sweep_angle - ghost * 0.07
            gpx = int(cx + d * math.cos(ga) * 2.1)
            gpy = int(cy + d * math.sin(ga))
            if 0 <= gpx < _W and 0 <= gpy < _H:
                trail_chars = ["▓", "▒", "░"]
                grid[gpy][gpx] = trail_chars[ghost - 1]

    # ── 4. Centre target reticle ──────────────────────────────────────────
    target_chars = [
        (0, -1, "▲"), (0, 1, "▼"), (-2, 0, "◄"), (2, 0, "►"),
        (-1, -1, "╔"), (1, -1, "╗"), (-1, 1, "╚"), (1, 1, "╝"),
        (0, 0, "◎"),
    ]
    for dx, dy, ch in target_chars:
        px, py = int(cx) + dx * 2, int(cy) + dy
        if 0 <= px < _W and 0 <= py < _H:
            grid[py][px] = ch

    # ── 5. Telemetry HUD (top-left) ───────────────────────────────────────
    telemetry = [
        f"SYS  {random.randint(60,99):3d}%",
        f"NET  {random.randint(10,99):3d} MB/s",
        f"LLM  READY",
        f"DB   {random.randint(60,99):3d} ms",
    ]
    for row_i, line in enumerate(telemetry):
        for col_i, ch in enumerate(line):
            if col_i < _W and row_i < _H:
                grid[row_i][col_i] = ch

    # ── 6. Telemetry HUD (top-right) ─────────────────────────────────────
    hud_right = [
        "DEVRECAI v1.0",
        f"TICK  {tick:05d}",
        "MODE  ANALYZE",
        f"CONF  {random.randint(80,99):3d}%",
    ]
    for row_i, line in enumerate(hud_right):
        start_col = _W - len(line)
        for col_i, ch in enumerate(line):
            col = start_col + col_i
            if 0 <= col < _W and row_i < _H:
                grid[row_i][col] = ch

    # ── 7. Status line at bottom centre ──────────────────────────────────
    status_frames = [
        "INITIALIZING ANALYSIS ENGINE",
        "LOADING TOOL KNOWLEDGE BASE",
        "CALIBRATING SCORING ENGINE",
        "READY FOR INPUT",
    ]
    status = status_frames[min(tick // 8, len(status_frames) - 1)]
    dots = "." * ((tick % 6) + 1)
    status_str = f"◈ {status}{dots} ◈"
    start = max(0, int(cx - len(status_str) / 2))
    for i, ch in enumerate(status_str):
        col = start + i
        if 0 <= col < _W:
            grid[_H - 2][col] = ch

    # ── 8. Press-any-key hint ─────────────────────────────────────────────
    if tick > 20:
        hint = "[ PRESS ANY KEY ]"
        h_start = max(0, int(cx - len(hint) / 2))
        for i, ch in enumerate(hint):
            col = h_start + i
            if 0 <= col < _W:
                grid[_H - 1][col] = ch

    return "\n".join("".join(row) for row in grid)


# ── Rich colour markup wrapper ────────────────────────────────────────────────

def _colorize(frame: str, tick: int) -> str:
    """
    Wrap the plain frame string in Rich markup to apply cyan/blue/white colours
    character by character based on the character type.
    """
    t = tick * 0.12
    lines = []
    for row_i, line in enumerate(frame.split("\n")):
        colored_chars: list[str] = []
        for col_i, ch in enumerate(line):
            # Distance from centre for intensity gradient
            cx, cy = _W / 2, _H / 2
            dist = math.sqrt(((col_i - cx) * 0.45) ** 2 + (row_i - cy) ** 2)

            if ch in "█▓":
                # Sweep line — bright cyan
                colored_chars.append(f"[bold cyan]{ch}[/bold cyan]")
            elif ch in "▒░":
                # Sweep trail — fading blue
                colored_chars.append(f"[blue]{ch}[/blue]")
            elif ch in "◎◈◄►▲▼╔╗╚╝":
                # Reticle / special — bright white
                colored_chars.append(f"[bold white]{ch}[/bold white]")
            elif ch in "─│":
                # Crosshair arms — steel blue
                colored_chars.append(f"[#4488AA]{ch}[/#4488AA]")
            elif ch in "●◉⊙":
                # Inner rings — bright cyan
                colored_chars.append(f"[bold cyan]{ch}[/bold cyan]")
            elif ch in "◎○∘":
                # Mid rings — cyan
                colored_chars.append(f"[cyan]{ch}[/cyan]")
            elif ch in "·⠂":
                # Outer rings — dark blue-grey
                colored_chars.append(f"[#1A4A6A]{ch}[/#1A4A6A]")
            elif ch.isalnum() or ch in "%/._-":
                # HUD text — bright cyan numbers
                if row_i < 4 or col_i > _W - 15:
                    colored_chars.append(f"[bold #00CFFF]{ch}[/bold #00CFFF]")
                else:
                    # Status line
                    brightness = 0.6 + 0.4 * math.sin(t * 3 + col_i * 0.3)
                    if brightness > 0.8:
                        colored_chars.append(f"[bold #39FFFF]{ch}[/bold #39FFFF]")
                    else:
                        colored_chars.append(f"[#00CFFF]{ch}[/#00CFFF]")
            elif ch == " ":
                colored_chars.append(" ")
            else:
                colored_chars.append(f"[#007799]{ch}[/#007799]")
        lines.append("".join(colored_chars))
    return "\n".join(lines)
