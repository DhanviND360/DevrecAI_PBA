"""
DevRecAI Unified LLM Client.

Supports:
  - Anthropic (Claude)
  - OpenAI (GPT)
  - Ollama (local — llama3.2:1b)
  - Google Gemini (gemini-2.5-flash)
  - Custom OpenAI-compatible endpoint

Includes streamed and non-streamed response modes.
Falls back through the chain: configured_provider → anthropic → openai → None (rule_based_only).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import AsyncGenerator, Optional

from devrecai.config.settings import get_settings
from devrecai.llm.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Hardcoded Gemini API key (user-provided)
GEMINI_API_KEY = "AIzaSyBV_-qheLtUAy0-YyzzG5Sl65GXMPr5hao"
GEMINI_MODEL = "gemini-2.5-flash-preview-04-17"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:1b"


class LLMError(Exception):
    """Raised when all LLM providers fail."""


class LLMClient:
    """Unified async LLM client with provider switching and fallback."""

    FALLBACK_CHAIN = ["anthropic", "openai"]

    def __init__(self, provider_override: Optional[str] = None) -> None:
        self._settings = get_settings()
        self._provider = provider_override or self._settings.llm.provider
        self._model = self._settings.llm.model

    # ─── Primary API ──────────────────────────────────────────────────────────

    async def complete(
        self,
        prompt: str,
        system: str = SYSTEM_PROMPT,
        max_tokens: int = 4096,
    ) -> str:
        """Non-streaming completion. Returns full response text."""
        if self._provider in ("ollama", "gemini"):
            # These providers don't use the standard fallback chain
            return await self._complete_with(self._provider, prompt, system, max_tokens)
        for provider in self._get_fallback_chain():
            try:
                return await self._complete_with(provider, prompt, system, max_tokens)
            except Exception as e:
                logger.warning(f"LLM provider {provider} failed: {e}")
        raise LLMError("All LLM providers failed. Check API keys in config.")

    async def stream(
        self,
        prompt: str,
        system: str = SYSTEM_PROMPT,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Streaming completion. Yields response text chunks."""
        provider = self._provider
        try:
            async for chunk in self._stream_with(provider, prompt, system, max_tokens):
                yield chunk
        except Exception as e:
            logger.warning(f"Streaming failed with {provider}: {e}")
            # Fallback: non-streaming complete
            try:
                text = await self.complete(prompt, system, max_tokens)
                yield text
            except LLMError:
                yield "[LLM unavailable — check API key in config]"

    # ─── Provider Implementations ─────────────────────────────────────────────

    async def _complete_with(
        self, provider: str, prompt: str, system: str, max_tokens: int
    ) -> str:
        if provider == "anthropic":
            return await self._anthropic_complete(prompt, system, max_tokens)
        elif provider == "openai":
            return await self._openai_complete(prompt, system, max_tokens)
        elif provider == "custom":
            return await self._custom_complete(prompt, system, max_tokens)
        elif provider == "ollama":
            return await self._ollama_complete(prompt, system, max_tokens)
        elif provider == "gemini":
            return await self._gemini_complete(prompt, system, max_tokens)
        raise ValueError(f"Unknown provider: {provider}")

    async def _stream_with(
        self, provider: str, prompt: str, system: str, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        if provider == "anthropic":
            async for chunk in self._anthropic_stream(prompt, system, max_tokens):
                yield chunk
        elif provider in ("openai", "custom"):
            async for chunk in self._openai_stream(prompt, system, max_tokens, provider):
                yield chunk
        elif provider == "ollama":
            async for chunk in self._ollama_stream(prompt, system, max_tokens):
                yield chunk
        elif provider == "gemini":
            # Gemini: use non-streaming and yield whole text
            text = await self._gemini_complete(prompt, system, max_tokens)
            yield text
        else:
            yield await self._complete_with(provider, prompt, system, max_tokens)

    # ─── Anthropic ────────────────────────────────────────────────────────────

    async def _anthropic_complete(self, prompt: str, system: str, max_tokens: int) -> str:
        import anthropic

        api_key = os.environ.get(self._settings.llm.api_key_env)
        if not api_key and self._settings.llm.provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY")

        client = anthropic.AsyncAnthropic(api_key=api_key)
        model = self._model if "claude" in self._model else "claude-sonnet-4-20250514"

        msg = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    async def _anthropic_stream(
        self, prompt: str, system: str, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        import anthropic

        api_key = os.environ.get(self._settings.llm.api_key_env) or os.environ.get("ANTHROPIC_API_KEY")
        client = anthropic.AsyncAnthropic(api_key=api_key)
        model = self._model if "claude" in self._model else "claude-sonnet-4-20250514"

        async with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    # ─── OpenAI ───────────────────────────────────────────────────────────────

    async def _openai_complete(self, prompt: str, system: str, max_tokens: int) -> str:
        from openai import AsyncOpenAI

        api_key = os.environ.get(self._settings.llm.api_key_env) or os.environ.get("OPENAI_API_KEY")
        client = AsyncOpenAI(api_key=api_key)
        model = self._model if "gpt" in self._model else "gpt-4o"

        resp = await client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content or ""

    async def _openai_stream(
        self, prompt: str, system: str, max_tokens: int, provider: str
    ) -> AsyncGenerator[str, None]:
        from openai import AsyncOpenAI

        if provider == "custom":
            api_key = os.environ.get("CUSTOM_LLM_KEY", "none")
            base_url = os.environ.get("CUSTOM_LLM_URL", "http://localhost:11434/v1")
        else:
            api_key = os.environ.get("OPENAI_API_KEY")
            base_url = None

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        model = self._model if provider != "custom" else self._model

        stream = await client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            stream=True,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def _custom_complete(self, prompt: str, system: str, max_tokens: int) -> str:
        return await self._openai_complete(prompt, system, max_tokens)

    # ─── Ollama ───────────────────────────────────────────────────────────────

    async def _ollama_complete(self, prompt: str, system: str, max_tokens: int) -> str:
        """Call local Ollama server using the /api/chat endpoint."""
        import aiohttp

        url = f"{OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": OLLAMA_MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise LLMError(f"Ollama returned {resp.status}: {text}")
                data = await resp.json()
                return data.get("message", {}).get("content", "")

    async def _ollama_stream(
        self, prompt: str, system: str, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """Stream from local Ollama server."""
        import aiohttp

        url = f"{OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": OLLAMA_MODEL,
            "stream": True,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                async for line in resp.content:
                    line = line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

    # ─── Google Gemini ────────────────────────────────────────────────────────

    async def _gemini_complete(self, prompt: str, system: str, max_tokens: int) -> str:
        """Call Google Gemini via the REST API."""
        import aiohttp

        api_key = GEMINI_API_KEY
        # Combine system + user prompt for Gemini
        full_prompt = f"{system}\n\n{prompt}"
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent?key={api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise LLMError(f"Gemini returned {resp.status}: {text}")
                data = await resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise LLMError("Gemini returned no candidates")
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(p.get("text", "") for p in parts)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _get_fallback_chain(self) -> list[str]:
        chain = [self._provider]
        for p in self.FALLBACK_CHAIN:
            if p != self._provider:
                chain.append(p)
        return chain
