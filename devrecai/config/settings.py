"""
DevRecAI Settings — Pydantic-Settings model.

Loads config from ~/.devrec/config.yaml with environment variable overrides.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default config directory
DEVREC_DIR = Path.home() / ".devrec"
CONFIG_PATH = DEVREC_DIR / "config.yaml"
REPORTS_DIR = Path.home() / "devrec-reports"


class LLMConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEVREC_LLM_")

    provider: Literal["anthropic", "openai", "custom", "ollama", "gemini"] = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key_env: str = "ANTHROPIC_API_KEY"
    timeout_seconds: int = 60
    streaming: bool = True
    custom_url: Optional[str] = None


class ScorerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEVREC_SCORER_")

    mode: Literal["rule_based", "ml_model", "hybrid"] = "hybrid"
    ml_model_path: str = str(DEVREC_DIR / "models" / "latest.json")
    confidence_threshold: float = 0.7


class OutputConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEVREC_OUTPUT_")

    directory: str = str(REPORTS_DIR)
    auto_export: bool = False
    formats: list[str] = ["markdown", "pdf"]


class ThemeConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEVREC_THEME_")

    name: Literal["retro-green", "amber", "ice-blue", "ghost-white"] = "retro-green"
    animations: bool = True
    boot_sequence: bool = True
    scanlines: bool = True


class FeedbackConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEVREC_FEEDBACK_")

    prompt_after_days: int = 30
    auto_retrain_every_n: int = 25


class Settings(BaseSettings):
    """Root settings model for DevRecAI."""

    model_config = SettingsConfigDict(
        env_prefix="DEVREC_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    llm: LLMConfig = Field(default_factory=LLMConfig)
    scorer: ScorerConfig = Field(default_factory=ScorerConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    theme: ThemeConfig = Field(default_factory=ThemeConfig)
    feedback: FeedbackConfig = Field(default_factory=FeedbackConfig)

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from ~/.devrec/config.yaml, falling back to defaults."""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH) as f:
                    raw = yaml.safe_load(f) or {}
                return cls.model_validate(raw)
            except Exception:
                # Corrupt config — silently fall back to defaults
                pass
        return cls()

    def save(self) -> None:
        """Persist current settings to ~/.devrec/config.yaml."""
        DEVREC_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)

    @property
    def llm_api_key(self) -> Optional[str]:
        """Resolve the active LLM API key from environment."""
        return os.environ.get(self.llm.api_key_env)

    def ensure_dirs(self) -> None:
        """Ensure all required directories exist."""
        DEVREC_DIR.mkdir(parents=True, exist_ok=True)
        (DEVREC_DIR / "models").mkdir(exist_ok=True)
        Path(self.output.directory).expanduser().mkdir(parents=True, exist_ok=True)


# Singleton accessor
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Return the global settings singleton, loading from disk if needed."""
    global _settings
    if _settings is None:
        _settings = Settings.load()
        _settings.ensure_dirs()
    return _settings


def reload_settings() -> Settings:
    """Force-reload settings from disk."""
    global _settings
    _settings = None
    return get_settings()
