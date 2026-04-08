"""
DevRecAI Unified Scorer.

Supports three modes:
  rule_based — deterministic, always available
  ml_model   — XGBoost inference (when model exists)
  hybrid     — ML if confidence > 0.7, else blend 50/50 with rule-based

Returns ranked tool lists per category with confidence and fit tags.
"""
from __future__ import annotations

import asyncio
from typing import Literal

from devrecai.config.settings import get_settings
from devrecai.engine.rules import compute_rule_score
from devrecai.engine.tools_db import get_all_categories, get_tools_by_category

CONFIDENCE_THRESHOLDS = {"HIGH": 85, "MEDIUM": 60, "LOW": 0}


def _confidence_label(score: float) -> str:
    if score >= 85:
        return "HIGH"
    elif score >= 60:
        return "MEDIUM"
    return "LOW"


def _fit_tag(score: float) -> str:
    if score >= 90:
        return "NATIVE FIT"
    elif score >= 80:
        return "STRONG FIT"
    elif score >= 60:
        return "GOOD FIT"
    elif score >= 40:
        return "MARGINAL FIT"
    return "POOR FIT"


class Scorer:
    """Unified DevOps tool scorer."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._mode = self._settings.scorer.mode
        self._ml_scorer = None

    def _get_ml_scorer(self):
        if self._ml_scorer is None:
            try:
                from devrecai.engine.ml_scorer import MLScorer
                self._ml_scorer = MLScorer()
            except Exception:
                pass
        return self._ml_scorer

    async def score(self, profile: dict) -> dict:
        """
        Score all tools in the knowledge base against the profile.

        Returns:
            {
                "categories": {
                    "CI/CD": [{"name": str, "score": float, "confidence": str, "fit_tag": str}, ...],
                    ...
                },
                "metadata": {"mode": str, "tool_count": int}
            }
        """
        categories = get_all_categories()
        result: dict = {"categories": {}, "metadata": {}}
        total_tools = 0

        for cat in categories:
            tools = get_tools_by_category(cat)
            if not tools:
                continue

            scored = []
            for tool in tools:
                score = await self._score_tool(tool, profile)
                scored.append({
                    "name": tool["name"],
                    "score": score,
                    "confidence": _confidence_label(score),
                    "fit_tag": _fit_tag(score),
                    "category": cat,
                })

            # Sort by score descending
            scored.sort(key=lambda x: x["score"], reverse=True)
            result["categories"][cat] = scored
            total_tools += len(scored)

        result["metadata"] = {
            "mode": self._mode,
            "tool_count": total_tools,
        }
        return result

    async def _score_tool(self, tool: dict, profile: dict) -> float:
        """Compute score for a single tool using the configured mode."""
        rule_score = compute_rule_score(tool, profile)

        if self._mode == "rule_based":
            return rule_score

        ml = self._get_ml_scorer()
        if self._mode == "ml_model":
            if ml and ml.is_ready():
                ml_score = await ml.predict(tool, profile)
                return ml_score
            return rule_score  # fallback

        # Hybrid mode
        if ml and ml.is_ready():
            ml_score = await ml.predict(tool, profile)
            ml_conf = await ml.confidence(tool, profile)
            if ml_conf >= self._settings.scorer.confidence_threshold:
                return ml_score
            else:
                return round((ml_score + rule_score) / 2.0, 1)

        return rule_score
