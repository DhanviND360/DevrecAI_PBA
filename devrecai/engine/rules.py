"""
DevRecAI Rule-Based Scoring Criteria.

Static weighted scoring functions for deterministic,
offline-capable tool evaluation.

Weights per spec:
  stack_compatibility  0.25
  team_size_fit        0.15
  budget_fit           0.15
  compliance_fit       0.15
  community_health     0.10
  learning_curve       0.10
  lock_in_risk         0.05
  integration_breadth  0.05
"""
from __future__ import annotations

from typing import Any

# ─── Weight Table ─────────────────────────────────────────────────────────────

WEIGHTS = {
    "stack_compatibility": 0.25,
    "team_size_fit": 0.15,
    "budget_fit": 0.15,
    "compliance_fit": 0.15,
    "community_health": 0.10,
    "learning_curve": 0.10,
    "lock_in_risk": 0.05,
    "integration_breadth": 0.05,
}

# ─── Budget Tier Mapping ───────────────────────────────────────────────────────

BUDGET_TIERS = {"oss": 0, "low": 1, "medium": 2, "enterprise": 3}
PRICING_TIERS = {"free": 0, "freemium": 1, "paid": 2, "enterprise": 3}

# ─── Team Size Mapping ────────────────────────────────────────────────────────

TEAM_SIZES = {"solo": 0, "small": 1, "mid": 2, "large": 3, "enterprise": 4}
TEAM_FIT_LEVELS = {
    "solo": [0, 1, 2],
    "small": [0, 1, 2, 3],
    "mid": [1, 2, 3, 4],
    "large": [2, 3, 4],
    "enterprise": [3, 4],
}

# ─── Scoring Functions ────────────────────────────────────────────────────────


def score_stack_compatibility(tool: dict, profile: dict) -> float:
    """How well tool integrates with user's language and cloud stack. 0.0-1.0"""
    score = 0.0
    checks = 0

    # Language compatibility
    user_langs = [l.lower() for l in profile.get("languages", [])]
    tool_langs = [l.lower() for l in tool.get("language_compatibility", [])]
    if user_langs and tool_langs:
        overlap = len(set(user_langs) & set(tool_langs))
        score += min(overlap / max(len(user_langs), 1), 1.0)
        checks += 1

    # Cloud compatibility
    user_clouds = [c.lower() for c in profile.get("cloud_provider", [])]
    tool_clouds = [c.lower() for c in tool.get("cloud_compatibility", [])]
    if user_clouds and tool_clouds:
        if "all" in tool_clouds or "agnostic" in tool_clouds:
            score += 1.0
        else:
            overlap = len(set(user_clouds) & set(tool_clouds))
            score += min(overlap / max(len(user_clouds), 1), 1.0)
        checks += 1

    return score / max(checks, 1)


def score_team_size_fit(tool: dict, profile: dict) -> float:
    """Complexity vs team capability match. 0.0-1.0"""
    user_size = profile.get("team_size", "small")
    maturity = profile.get("devops_maturity", "intermediate")
    tool_fits = tool.get("team_size_fit", [])
    learning_curve = tool.get("learning_curve", 3)  # 1-5

    size_idx = TEAM_SIZES.get(user_size, 1)
    optimal_indices = TEAM_FIT_LEVELS.get(user_size, [1, 2, 3])

    # Check if tool's team fit overlaps
    fit_score = 0.5
    if tool_fits:
        tool_size_indices = [TEAM_SIZES.get(s.lower(), 2) for s in tool_fits]
        overlap = len(set(optimal_indices) & set(tool_size_indices))
        fit_score = min(overlap / max(len(optimal_indices), 1), 1.0)

    # Penalize high learning curve for beginners
    maturity_map = {"beginner": 1, "intermediate": 2, "advanced": 3, "sre": 4}
    maturity_level = maturity_map.get(maturity, 2)
    if learning_curve > maturity_level + 1:
        fit_score *= 0.7  # 30% penalty for mismatched complexity

    return min(fit_score, 1.0)


def score_budget_fit(tool: dict, profile: dict) -> float:
    """License cost vs declared budget tier. 0.0-1.0"""
    user_budget = BUDGET_TIERS.get(profile.get("budget_tier", "low"), 1)
    tool_pricing = tool.get("pricing_tier", "paid").lower()
    tool_tier = PRICING_TIERS.get(tool_pricing, 2)

    if tool_tier == 0:  # free — always fits
        return 1.0
    elif tool_tier <= user_budget:
        return 1.0
    elif tool_tier == user_budget + 1:
        return 0.5  # slightly over budget
    else:
        return 0.1  # well over budget


def score_compliance_fit(tool: dict, profile: dict) -> float:
    """Tool certifications vs required compliance. 0.0-1.0"""
    required = set(c.lower() for c in profile.get("compliance", []) if c.lower() != "none")
    if not required:
        return 1.0  # No compliance required — any tool fits

    tool_certs = set(c.lower() for c in tool.get("compliance_certifications", []))
    if not tool_certs:
        return 0.3  # Tool has no certs but compliance required

    overlap = len(required & tool_certs)
    return min(overlap / len(required), 1.0)


def score_community_health(tool: dict, profile: dict) -> float:
    """Stars, release cadence, community health score. 0.0-1.0"""
    raw = tool.get("community_health_score", 50)
    return min(raw / 100.0, 1.0)


def score_learning_curve(tool: dict, profile: dict) -> float:
    """Onboarding cost vs team maturity. 0.0-1.0"""
    curve = tool.get("learning_curve", 3)  # 1=easy, 5=expert
    maturity_map = {"beginner": 1, "intermediate": 2, "advanced": 3, "sre": 4}
    maturity = maturity_map.get(profile.get("devops_maturity", "intermediate"), 2)
    # If learning curve <= maturity, score = 1.0; otherwise penalize
    if curve <= maturity:
        return 1.0
    else:
        return max(1.0 - (curve - maturity) * 0.25, 0.0)


def score_lock_in_risk(tool: dict, profile: dict) -> float:
    """Vendor dependency penalty. 0.0-1.0 (higher = less lock-in = better)"""
    risk_map = {"low": 1.0, "medium": 0.6, "high": 0.2}
    return risk_map.get(tool.get("vendor_lock_in_risk", "medium"), 0.6)


def score_integration_breadth(tool: dict, profile: dict) -> float:
    """How many existing stack tools it connects with. 0.0-1.0"""
    existing = [t.strip().lower() for t in profile.get("existing_tools", "").split(",") if t.strip()]
    tool_integrations = [i.lower() for i in tool.get("integrations", [])]

    if not existing:
        # Use raw count of integrations as proxy (normalize by 30)
        return min(len(tool_integrations) / 30.0, 1.0)

    overlap = len(set(existing) & set(tool_integrations))
    return min(overlap / max(len(existing), 1), 1.0)


# ─── Combined Rule Scorer ─────────────────────────────────────────────────────

SCORERS = {
    "stack_compatibility": score_stack_compatibility,
    "team_size_fit": score_team_size_fit,
    "budget_fit": score_budget_fit,
    "compliance_fit": score_compliance_fit,
    "community_health": score_community_health,
    "learning_curve": score_learning_curve,
    "lock_in_risk": score_lock_in_risk,
    "integration_breadth": score_integration_breadth,
}


def compute_rule_score(tool: dict, profile: dict) -> float:
    """Compute weighted rule-based score for a tool. Returns 0-100."""
    total = 0.0
    for criterion, weight in WEIGHTS.items():
        fn = SCORERS[criterion]
        raw = fn(tool, profile)
        total += raw * weight
    return round(total * 100, 1)


def compute_per_criterion(tool: dict, profile: dict) -> dict[str, float]:
    """Return per-criterion scores for explainability."""
    return {
        criterion: round(fn(tool, profile) * 100, 1)
        for criterion, fn in SCORERS.items()
    }
