"""
DevRecAI Explainer — Recommendation explainability layer.

Calls LLM with structured prompts, parses JSON responses,
and streams explanations into the TUI explanation panel.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from devrecai.llm.client import LLMClient
from devrecai.llm.prompts import (
    build_recommendation_explanation_prompt,
    build_single_tool_deep_dive_prompt,
    build_comparison_prompt,
    build_report_generation_prompt,
)

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> Any:
    """Extract JSON from a text response (handles markdown code blocks)."""
    # Remove markdown code blocks if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object within the text
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


class Explainer:
    """LLM-powered explainability layer for tool recommendations."""

    def __init__(self) -> None:
        self._client = LLMClient()

    async def explain(self, profile: dict, results: dict) -> dict:
        """
        Generate AI explanations for top tools in each category.
        Returns dict keyed by tool_name with explanation fields.
        """
        # Prepare top-3 tools per category for the prompt
        top_tools: dict = {}
        for cat, tools in results.get("categories", {}).items():
            top_tools[cat] = [
                {"name": t["name"], "score": t["score"]}
                for t in tools[:3]
            ]

        prompt = build_recommendation_explanation_prompt(profile, top_tools)

        try:
            response = await self._client.complete(prompt, max_tokens=4096)
            data = _extract_json(response)
            # Normalize: could be {tool_name: {...}} or [{tool_name: ..., ...}]
            if isinstance(data, list):
                return {item.get("tool_name", f"tool_{i}"): item for i, item in enumerate(data)}
            elif isinstance(data, dict):
                return data
            return {}
        except Exception as e:
            logger.warning(f"LLM explanation failed: {e}")
            return {}

    async def deep_dive(self, profile: dict, tool_name: str, score: float = 0) -> dict:
        """
        Generate a deep-dive explanation for a single tool.
        Returns the parsed explanation dict.
        """
        prompt = build_single_tool_deep_dive_prompt(profile, tool_name, score)
        try:
            response = await self._client.complete(prompt, max_tokens=2048)
            data = _extract_json(response)
            if isinstance(data, dict):
                return data
            return {"fit_summary": response, "confidence_level": "MEDIUM"}
        except Exception as e:
            logger.warning(f"LLM deep dive failed: {e}")
            return {
                "fit_summary": f"LLM unavailable: {e}",
                "confidence_level": "LOW",
            }

    async def compare(self, profile: dict, tool_list: list[str]) -> dict:
        """Generate a side-by-side comparison matrix."""
        prompt = build_comparison_prompt(profile, tool_list)
        try:
            response = await self._client.complete(prompt, max_tokens=3000)
            return _extract_json(response) or {}
        except Exception as e:
            logger.warning(f"LLM comparison failed: {e}")
            return {}

    async def generate_report_content(self, profile: dict, full_results: dict) -> str:
        """Generate the full Markdown report content via LLM."""
        prompt = build_report_generation_prompt(profile, full_results)
        try:
            return await self._client.complete(prompt, max_tokens=6000)
        except Exception as e:
            logger.warning(f"LLM report generation failed: {e}")
            return f"# DevRecAI Report\n\nLLM unavailable: {e}\n\nRule-based results appended below."
