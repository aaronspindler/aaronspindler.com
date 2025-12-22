import logging
from enum import Enum
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMService:
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
        if model is None:
            model = cls.DEFAULT_OPENAI_MODEL if provider == LLMProvider.OPENAI else cls.DEFAULT_ANTHROPIC_MODEL

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
            raise ImportError("openai package not installed. Run: pip install openai") from None
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
            raise ImportError("anthropic package not installed. Run: pip install anthropic") from None
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise

    @classmethod
    def _track_usage(cls, provider: str, model: str, prompt: str, response: str) -> None:
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
