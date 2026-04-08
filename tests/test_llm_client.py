"""
Unit tests for the LLM client.
Tests provider switching, fallback chain, and response parsing.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestLLMClientInit:
    def test_default_provider(self):
        from devrecai.llm.client import LLMClient
        client = LLMClient()
        assert client._provider in ("anthropic", "openai", "custom")

    def test_fallback_chain_includes_all(self):
        from devrecai.llm.client import LLMClient
        client = LLMClient()
        chain = client._get_fallback_chain()
        assert len(chain) >= 1
        assert client._provider in chain


class TestPromptBuilders:
    def test_recommendation_prompt(self):
        from devrecai.llm.prompts import build_recommendation_explanation_prompt
        profile = {"project_name": "TestProj", "team_size": "small"}
        tools = {"CI/CD": [{"name": "GitHub Actions", "score": 94}]}
        prompt = build_recommendation_explanation_prompt(profile, tools)
        assert "TestProj" in prompt
        assert "GitHub Actions" in prompt
        assert "JSON" in prompt

    def test_deep_dive_prompt(self):
        from devrecai.llm.prompts import build_single_tool_deep_dive_prompt
        profile = {"project_name": "TestProj"}
        prompt = build_single_tool_deep_dive_prompt(profile, "Terraform", 88.0)
        assert "Terraform" in prompt
        assert "88.0" in prompt

    def test_comparison_prompt(self):
        from devrecai.llm.prompts import build_comparison_prompt
        profile = {"project_name": "TestProj"}
        prompt = build_comparison_prompt(profile, ["GitHub Actions", "GitLab CI"])
        assert "GitHub Actions" in prompt
        assert "GitLab CI" in prompt


class TestExplainerJSONParsing:
    def test_extract_json_clean(self):
        from devrecai.llm.explainer import _extract_json
        data = _extract_json('{"key": "value"}')
        assert data == {"key": "value"}

    def test_extract_json_with_markdown(self):
        from devrecai.llm.explainer import _extract_json
        data = _extract_json('```json\n{"key": "value"}\n```')
        assert data == {"key": "value"}

    def test_extract_json_invalid(self):
        from devrecai.llm.explainer import _extract_json
        data = _extract_json("not json at all")
        assert data == {}
