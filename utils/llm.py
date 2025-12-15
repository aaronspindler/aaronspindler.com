"""
LLM service wrapper for OpenAI and Anthropic with automatic usage tracking.

Usage:
    from utils.services import LLMService, LLMProvider

    # OpenAI
    response = LLMService.chat(
        prompt="What is the capital of France?",
        provider=LLMProvider.OPENAI,
        model="gpt-4o"
    )

    # Anthropic
    response = LLMService.chat(
        prompt="What is the capital of France?",
        provider=LLMProvider.ANTHROPIC,
        model="claude-3-5-sonnet-20241022"
    )

    # Default provider (OpenAI with gpt-4o-mini)
    response = LLMService.chat("What is the capital of France?")
"""

import logging
from enum import Enum
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMService:
    """
    Abstract service for calling LLM APIs with automatic usage tracking.

    All calls are tracked in the LLMUsage model.
    """

    DEFAULT_PROVIDER = LLMProvider.OPENAI
    DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
    DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"

    @classmethod
    def chat(
        cls,
        prompt: str,
        provider: LLMProvider = DEFAULT_PROVIDER,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Send a chat completion request to an LLM provider.

        Args:
            prompt: The user message to send
            provider: LLM provider to use (OpenAI or Anthropic)
            model: Model name (uses defaults if not specified)
            system_prompt: System message to set context
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens in response

        Returns:
            The LLM's response text

        Raises:
            ValueError: If API key is not configured or provider is invalid
            Exception: If the API call fails
        """
        # Set default model based on provider
        if model is None:
            model = cls.DEFAULT_OPENAI_MODEL if provider == LLMProvider.OPENAI else cls.DEFAULT_ANTHROPIC_MODEL

        # Route to appropriate provider
        if provider == LLMProvider.OPENAI:
            response = cls._call_openai(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        elif provider == LLMProvider.ANTHROPIC:
            response = cls._call_anthropic(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        # Track usage
        cls._track_usage(
            provider=provider.value,
            model=model,
            prompt=prompt,
            response=response,
        )

        return response

    @classmethod
    def _call_openai(
        cls,
        prompt: str,
        model: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
    ) -> str:
        """Call OpenAI API."""
        if not settings.OPENAI_KEY:
            raise ValueError("OPENAI_KEY is not configured in settings")

        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.OPENAI_KEY)

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content

        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

    @classmethod
    def _call_anthropic(
        cls,
        prompt: str,
        model: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
    ) -> str:
        """Call Anthropic API."""
        if not settings.ANTHROPIC_KEY:
            raise ValueError("ANTHROPIC_KEY is not configured in settings")

        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=settings.ANTHROPIC_KEY)

            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens or 1024,  # Anthropic requires max_tokens
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            response = client.messages.create(**kwargs)
            return response.content[0].text

        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise

    @classmethod
    def _track_usage(cls, provider: str, model: str, prompt: str, response: str) -> None:
        """Track LLM usage in database."""
        try:
            from utils.models import LLMUsage

            LLMUsage.objects.create(
                provider=provider,
                model=model,
                prompt=prompt,
                response=response,
            )
            logger.info(f"Tracked LLM usage: {provider}/{model}")
        except Exception as e:
            logger.error(f"Failed to track LLM usage: {e}")

