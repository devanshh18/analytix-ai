"""
Analytix AI — LLM Service.
Pluggable architecture: GroqLLM (primary), RuleBasedLLM (fallback).
"""
import os
import logging
from typing import Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseLLM(ABC):
    """Abstract base class for LLM backends."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "", max_tokens: int = 2048) -> str:
        pass

    @abstractmethod
    def generate_json(self, prompt: str, system_prompt: str = "", max_tokens: int = 4096) -> dict | list:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass


class GroqLLM(BaseLLM):
    """Groq-powered LLM backend — fast inference with LLaMA3/Mixtral."""

    def __init__(self):
        self._service = None

    def _get_service(self):
        if self._service is None:
            from services.groq_service import get_groq_service
            self._service = get_groq_service()
        return self._service

    def is_available(self) -> bool:
        try:
            api_key = os.getenv("GROQ_API_KEY")
            return bool(api_key)
        except Exception:
            return False

    def generate(self, prompt: str, system_prompt: str = "", max_tokens: int = 2048) -> str:
        service = self._get_service()
        return service.chat(
            user_prompt=prompt,
            system_prompt=system_prompt or "You are a senior data analyst.",
            max_tokens=max_tokens,
        )

    def generate_json(self, prompt: str, system_prompt: str = "", max_tokens: int = 4096,
                       temperature: float = 0.2) -> dict | list:
        service = self._get_service()
        return service.chat_json(
            user_prompt=prompt,
            system_prompt=system_prompt or "You are a senior data analyst. Always respond with valid JSON.",
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def chat_with_history(self, messages: list[dict], system_prompt: str = "",
                          max_tokens: int = 2048, json_mode: bool = False) -> str:
        service = self._get_service()
        return service.chat_with_history(
            messages=messages,
            system_prompt=system_prompt or "You are a senior data analyst.",
            max_tokens=max_tokens,
            json_mode=json_mode,
        )


class RuleBasedLLM(BaseLLM):
    """Fallback rule-based 'LLM' — works without any API key."""

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, system_prompt: str = "", max_tokens: int = 2048) -> str:
        return "Analysis completed using rule-based engine."

    def generate_json(self, prompt: str, system_prompt: str = "", max_tokens: int = 4096) -> dict | list:
        return {}


def get_llm_service() -> BaseLLM:
    """Factory function to get the configured LLM service."""
    backend = os.getenv("LLM_BACKEND", "rule_based").lower()

    if backend == "groq":
        groq_llm = GroqLLM()
        if groq_llm.is_available():
            logger.info("Using Groq LLM backend")
            return groq_llm
        logger.warning("Groq LLM not available (no API key). Falling back to rule-based.")

    return RuleBasedLLM()
