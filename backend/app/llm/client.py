"""LiteLLM unified async client with timeout, error normalization, and secret shielding."""

import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, Optional

import litellm

from app.core.config import settings
from app.llm.schemas import MergeProposal

logger = logging.getLogger(__name__)

# Suppress litellm noisy telemetry & verbose logging
litellm.telemetry = False
litellm.drop_params = True


class LLMError(Exception):
    """Base exception for LLM operations."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class LLMConfigurationError(LLMError):
    """Raised when LLM configuration (API key, model) is missing or invalid."""

    def __init__(self, message: str = "LLM configuration is missing or invalid."):
        super().__init__(message, status_code=401)


class LLMTimeoutError(LLMError):
    """Raised when an LLM call exceeds the configured timeout."""

    def __init__(self, message: str = "LLM request timed out."):
        super().__init__(message, status_code=504)


class LLMProviderError(LLMError):
    """Raised when the upstream LLM provider returns an error."""

    def __init__(self, message: str = "Upstream LLM provider failure."):
        super().__init__(message, status_code=502)


class LLMResponseParsingError(LLMError):
    """Raised when LLM output cannot be parsed into the required schema."""

    def __init__(self, message: str = "Failed to parse structured LLM response."):
        super().__init__(message, status_code=502)


class LLMClient:
    """LiteLLM wrapper for provider-swappable, async LLM completions."""

    def __init__(
        self,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout_seconds: Optional[int] = None,
    ):
        self.provider = provider or settings.LLM_PROVIDER or "openrouter"
        self.raw_model = model or settings.LLM_MODEL or "openai/gpt-4o-mini"
        self.api_key = api_key if api_key is not None else settings.OPENROUTER_API_KEY
        self.temperature = (
            temperature if temperature is not None else settings.LLM_TEMPERATURE
        )
        self.timeout_seconds = timeout_seconds or settings.LLM_TIMEOUT_SECONDS

        # Normalize model string for LiteLLM
        self.model = self._normalize_model_name(self.raw_model, self.provider)

    @staticmethod
    def _normalize_model_name(model: str, provider: str) -> str:
        """Ensure provider prefix is attached for LiteLLM dispatch if needed."""
        cleaned = model.strip()
        if provider == "openrouter" and not cleaned.startswith("openrouter/"):
            return f"openrouter/{cleaned}"
        return cleaned

    def validate_configuration(self) -> None:
        """Verify essential configuration before executing calls."""
        if not self.model:
            raise LLMConfigurationError("LLM model name must not be empty.")

        # If using OpenRouter, require an API key
        if "openrouter" in self.model.lower() and not self.api_key:
            raise LLMConfigurationError(
                "OPENROUTER_API_KEY is not configured. Please set OPENROUTER_API_KEY."
            )

    async def complete_merge_proposal(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> MergeProposal:
        """
        Execute an async completion with LiteLLM, requesting structured JSON output
        and validating it against the MergeProposal schema.
        """
        self.validate_configuration()

        start_time = time.monotonic()
        logger.info(
            "Initiating LLM completion with model '%s' (temperature=%.2f, timeout=%ds)",
            self.model,
            self.temperature,
            self.timeout_seconds,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "timeout": self.timeout_seconds,
            "response_format": {"type": "json_object"},
        }

        if self.api_key:
            kwargs["api_key"] = self.api_key

        try:
            response = await asyncio.wait_for(
                litellm.acompletion(**kwargs),
                timeout=float(self.timeout_seconds),
            )
        except asyncio.TimeoutError as exc:
            duration = time.monotonic() - start_time
            logger.error("LLM completion timed out after %.2fs", duration)
            raise LLMTimeoutError(f"LLM request timed out after {self.timeout_seconds} seconds.") from exc
        except litellm.exceptions.AuthenticationError as exc:
            logger.error("LLM authentication failed: %s", type(exc).__name__)
            raise LLMConfigurationError("LLM authentication failed. Check your API credentials.") from exc
        except (litellm.exceptions.RateLimitError, litellm.exceptions.ServiceUnavailableError) as exc:
            logger.error("LLM provider unavailable or rate-limited: %s", type(exc).__name__)
            raise LLMProviderError(f"LLM provider rate limit or service unavailability: {exc}") from exc
        except litellm.exceptions.APIError as exc:
            logger.error("LLM provider API error: %s", type(exc).__name__)
            raise LLMProviderError(f"LLM provider API error: {exc}") from exc
        except Exception as exc:
            logger.exception("Unexpected error during LLM completion: %s", type(exc).__name__)
            raise LLMProviderError(f"LLM call failed: {exc}") from exc

        duration = time.monotonic() - start_time
        logger.info("LLM completion received in %.2fs", duration)

        # Extract text content safely
        raw_text = self._extract_raw_content(response)
        if not raw_text or not raw_text.strip():
            logger.error("Empty completion response returned by LLM")
            raise LLMResponseParsingError("LLM returned an empty response.")

        # Parse and validate JSON
        parsed_dict = self._parse_json_content(raw_text)
        try:
            # Set model metadata on proposal
            if "model" not in parsed_dict or not parsed_dict["model"]:
                parsed_dict["model"] = self.model
            proposal = MergeProposal(**parsed_dict)
        except Exception as exc:
            logger.error("Pydantic validation failed on LLM response: %s", exc)
            raise LLMResponseParsingError(f"Invalid proposal schema from LLM: {exc}") from exc

        logger.info("Validated MergeProposal status: '%s'", proposal.status)
        return proposal

    @staticmethod
    def _extract_raw_content(response: Any) -> str:
        """Safely extract raw text from LiteLLM response."""
        try:
            choices = response.get("choices") if isinstance(response, dict) else getattr(response, "choices", None)
            if not choices or len(choices) == 0:
                return ""
            first_choice = choices[0]
            message = first_choice.get("message") if isinstance(first_choice, dict) else getattr(first_choice, "message", None)
            if not message:
                return ""
            content = message.get("content") if isinstance(message, dict) else getattr(message, "content", "")
            return content or ""
        except Exception as exc:
            logger.warning("Failed to extract content from LiteLLM response: %s", exc)
            return ""

    @staticmethod
    def _parse_json_content(raw_text: str) -> Dict[str, Any]:
        """Strip possible markdown code blocks and parse JSON safely."""
        text = raw_text.strip()
        # Strip ```json ... ``` code fence if present
        if text.startswith("```"):
            fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if fence_match:
                text = fence_match.group(1).strip()

        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("Expected JSON root to be an object.")
            return data
        except json.JSONDecodeError as exc:
            logger.error("Failed to decode JSON from LLM: %s", exc)
            raise LLMResponseParsingError(f"LLM response is not valid JSON: {exc}") from exc
