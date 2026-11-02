"""LiteLLM unified async client with timeout, fallback, retry, error normalization, and secret shielding."""

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

# Prevent LiteLLM from blocking on raw.githubusercontent.com downloads
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

import litellm

from app.core.config import settings
from app.llm.schemas import MergeProposal

logger = logging.getLogger(__name__)

# Suppress litellm noisy telemetry & verbose logging
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
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


def _parse_fallback_models() -> List[str]:
    """Parse comma-separated fallback models from settings."""
    raw = settings.LLM_FALLBACK_MODELS or ""
    return [m.strip() for m in raw.split(",") if m.strip()]


class LLMClient:
    """LiteLLM wrapper for provider-swappable, async LLM completions with fallback and retry."""

    def __init__(
        self,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
        fallback_models: Optional[List[str]] = None,
    ):
        self.provider = provider or settings.LLM_PROVIDER or "openrouter"
        self.raw_model = model or settings.LLM_MODEL or "openai/gpt-4o-mini"
        self.api_key = api_key if api_key is not None else settings.OPENROUTER_API_KEY
        self.temperature = (
            temperature if temperature is not None else settings.LLM_TEMPERATURE
        )
        self.timeout_seconds = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
        self.max_retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES

        # Normalize model string for LiteLLM
        self.model = self._normalize_model_name(self.raw_model, self.provider)

        # Build ordered list of models to try: primary + fallbacks
        raw_fallbacks = fallback_models if fallback_models is not None else _parse_fallback_models()
        self._model_chain: List[str] = [self.model]
        for fb in raw_fallbacks:
            normalized = self._normalize_model_name(fb, self.provider)
            if normalized != self.model and normalized not in self._model_chain:
                self._model_chain.append(normalized)

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

    async def _attempt_completion(
        self,
        target_model: str,
        messages: List[Dict[str, str]],
        timeout: float,
    ) -> Any:
        """Execute a single LLM completion attempt against one model with timeout."""
        kwargs: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": self.temperature,
            "timeout": int(timeout),
            "response_format": {"type": "json_object"},
        }

        if self.api_key:
            kwargs["api_key"] = self.api_key

        return await asyncio.wait_for(
            litellm.acompletion(**kwargs),
            timeout=float(timeout),
        )

    async def complete_structured_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """
        Execute an async completion with LiteLLM, requesting structured JSON output
        and returning the decoded dictionary.

        Implements a robust retry-with-fallback strategy:
        1. Try each model in the chain (primary, then fallbacks).
        2. For each model, retry up to max_retries on transient failures.
        3. Use exponential backoff between retries.
        """
        self.validate_configuration()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        last_error: Optional[Exception] = None
        models_tried: List[str] = []

        for model_idx, target_model in enumerate(self._model_chain):
            per_model_timeout = self.timeout_seconds

            for attempt in range(1, self.max_retries + 1):
                start_time = time.monotonic()
                models_tried.append(target_model)
                logger.info(
                    "LLM completion: model='%s' attempt=%d/%d timeout=%ds",
                    target_model,
                    attempt,
                    self.max_retries,
                    per_model_timeout,
                )

                try:
                    response = await self._attempt_completion(
                        target_model=target_model,
                        messages=messages,
                        timeout=float(per_model_timeout),
                    )
                    duration = time.monotonic() - start_time
                    logger.info("LLM completion received in %.2fs from '%s'", duration, target_model)

                    raw_text = self._extract_raw_content(response)
                    if not raw_text or not raw_text.strip():
                        logger.warning("Empty completion response from '%s' (attempt %d)", target_model, attempt)
                        last_error = LLMResponseParsingError("LLM returned an empty response.")
                        continue  # retry same model

                    parsed_dict = self._parse_json_content(raw_text)

                    # Track which model actually responded
                    parsed_dict["_resolved_model"] = target_model
                    return parsed_dict

                except (asyncio.TimeoutError, TimeoutError, litellm.exceptions.Timeout):
                    duration = time.monotonic() - start_time
                    logger.warning(
                        "LLM timeout after %.2fs on model '%s' (attempt %d/%d)",
                        duration, target_model, attempt, self.max_retries,
                    )
                    last_error = LLMTimeoutError(
                        f"LLM request timed out after {per_model_timeout}s on model '{target_model}'."
                    )
                    # Don't retry same model on timeout — fall through to next model
                    break

                except litellm.exceptions.AuthenticationError as exc:
                    logger.error("LLM authentication failed on '%s': %s", target_model, type(exc).__name__)
                    raise LLMConfigurationError("LLM authentication failed. Check your API credentials.") from exc

                except (litellm.exceptions.RateLimitError, litellm.exceptions.ServiceUnavailableError) as exc:
                    duration = time.monotonic() - start_time
                    logger.warning(
                        "LLM rate-limited/unavailable on '%s' (attempt %d, %.2fs): %s",
                        target_model, attempt, duration, exc,
                    )
                    last_error = LLMProviderError(f"LLM provider rate limit or service unavailability: {exc}")
                    if attempt < self.max_retries:
                        backoff = min(2 ** attempt, 10)
                        logger.info("Retrying in %ds...", backoff)
                        await asyncio.sleep(backoff)
                        continue
                    # Exhausted retries on this model, try next
                    break

                except litellm.exceptions.APIError as exc:
                    duration = time.monotonic() - start_time
                    logger.warning(
                        "LLM API error on '%s' (attempt %d, %.2fs): %s",
                        target_model, attempt, duration, exc,
                    )
                    last_error = LLMProviderError(f"LLM provider API error: {exc}")
                    if attempt < self.max_retries:
                        backoff = min(2 ** attempt, 8)
                        await asyncio.sleep(backoff)
                        continue
                    break

                except LLMResponseParsingError:
                    raise

                except Exception as exc:
                    duration = time.monotonic() - start_time
                    logger.warning(
                        "Unexpected error on '%s' (attempt %d, %.2fs): %s: %s",
                        target_model, attempt, duration, type(exc).__name__, exc,
                    )
                    last_error = LLMProviderError(f"LLM call failed: {exc}")
                    if attempt < self.max_retries:
                        backoff = min(2 ** attempt, 8)
                        await asyncio.sleep(backoff)
                        continue
                    break

            # Log before trying next fallback
            if model_idx < len(self._model_chain) - 1:
                next_model = self._model_chain[model_idx + 1]
                logger.info("Falling back from '%s' to '%s'", target_model, next_model)

        # All models and retries exhausted
        tried_str = ", ".join(dict.fromkeys(models_tried))  # unique, ordered
        if isinstance(last_error, LLMTimeoutError):
            raise LLMTimeoutError(
                f"LLM request timed out after trying models: [{tried_str}]. "
                f"Timeout was {self.timeout_seconds}s per model."
            )
        if isinstance(last_error, LLMError):
            raise last_error
        if last_error:
            raise LLMProviderError(f"All LLM models failed. Last error: {last_error}") from last_error
        raise LLMProviderError(f"All LLM models failed: [{tried_str}]")

    async def complete_merge_proposal(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> MergeProposal:
        """
        Execute an async completion with LiteLLM, requesting structured JSON output
        and validating it against the MergeProposal schema.
        """
        parsed_dict = await self.complete_structured_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        resolved_model = parsed_dict.pop("_resolved_model", self.model)

        try:
            if "model" not in parsed_dict or not parsed_dict["model"]:
                parsed_dict["model"] = resolved_model
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
