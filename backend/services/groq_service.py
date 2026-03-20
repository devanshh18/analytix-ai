"""
Analytix AI — Groq API Service.
Reusable client for all LLM interactions via Groq's ultra-fast inference.
Includes model fallback for rate limit resilience.
"""
import os
import re
import json
import logging
import time
from typing import Optional
from groq import Groq

logger = logging.getLogger(__name__)

# Models ordered by preference — if primary is rate-limited, try fallbacks
FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]


class GroqService:
    """Centralized Groq API client with model fallback for rate limits."""

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        self.client = Groq(api_key=api_key)
        self.primary_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def _get_models(self):
        """Return model list with primary first, then fallbacks."""
        models = [self.primary_model]
        for m in FALLBACK_MODELS:
            if m != self.primary_model:
                models.append(m)
        return models

    def _extract_retry_time(self, error_msg: str) -> str:
        """Extract the retry-after time from Groq rate limit error message."""
        match = re.search(r'try again in ([\d]+m[\d\.]+s|[\d\.]+s|[\d]+m)', error_msg)
        if match:
            return match.group(1)
        return ""

    def chat(
        self,
        user_prompt: str,
        system_prompt: str = "You are a senior data analyst.",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        """Send a chat completion request. Automatically falls back to smaller models on rate limit."""
        models = self._get_models()
        last_error = None

        for model in models:
            try:
                kwargs = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                response = self.client.chat.completions.create(**kwargs)
                if model != self.primary_model:
                    logger.info(f"Used fallback model: {model}")
                return response.choices[0].message.content or ""

            except Exception as e:
                last_error = e
                error_str = str(e)
                if "429" in error_str or "rate_limit" in error_str:
                    logger.warning(f"Rate limited on {model}, trying next model...")
                    continue
                else:
                    logger.error(f"Groq API error ({model}): {e}")
                    raise
        # Extract retry-after time from error message
        retry_time = self._extract_retry_time(str(last_error))
        msg = f"Rate limit exceeded. Please try again in {retry_time}." if retry_time else "Rate limit exceeded. Please try again later."
        logger.error(f"All models rate-limited. {msg}")
        raise RuntimeError(msg)

    def chat_json(
        self,
        user_prompt: str,
        system_prompt: str = "You are a senior data analyst. Always respond with valid JSON.",
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> dict | list:
        """Send a request and parse the response as JSON."""
        raw = self.chat(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
        )
        # Try to parse JSON from the response
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
            if json_match:
                return json.loads(json_match.group(1).strip())
            # Try to find JSON array or object
            for start_char, end_char in [('[', ']'), ('{', '}')]:
                start = raw.find(start_char)
                end = raw.rfind(end_char)
                if start != -1 and end != -1 and end > start:
                    try:
                        return json.loads(raw[start:end + 1])
                    except json.JSONDecodeError:
                        continue
            logger.error(f"Failed to parse JSON from Groq response: {raw[:200]}")
            raise ValueError(f"Could not parse JSON from LLM response")

    def chat_with_history(
        self,
        messages: list[dict],
        system_prompt: str = "You are a senior data analyst.",
        temperature: float = 0.4,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> str:
        """Send a multi-turn conversation with model fallback."""
        models = self._get_models()
        last_error = None

        for model in models:
            try:
                all_messages = [{"role": "system", "content": system_prompt}] + messages
                kwargs = {
                    "model": model,
                    "messages": all_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                response = self.client.chat.completions.create(**kwargs)
                if model != self.primary_model:
                    logger.info(f"Used fallback model: {model}")
                return response.choices[0].message.content or ""

            except Exception as e:
                last_error = e
                error_str = str(e)
                if "429" in error_str or "rate_limit" in error_str:
                    logger.warning(f"Rate limited on {model}, trying next model...")
                    continue
                else:
                    logger.error(f"Groq API error ({model}): {e}")
                    raise

        retry_time = self._extract_retry_time(str(last_error))
        msg = f"Rate limit exceeded. Please try again in {retry_time}." if retry_time else "Rate limit exceeded. Please try again later."
        logger.error(f"All models rate-limited. {msg}")
        raise RuntimeError(msg)


# Singleton instance
_instance: Optional[GroqService] = None


def get_groq_service() -> GroqService:
    """Get or create the singleton GroqService instance."""
    global _instance
    if _instance is None:
        _instance = GroqService()
    return _instance
