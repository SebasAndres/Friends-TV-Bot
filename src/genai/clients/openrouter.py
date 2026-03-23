import json
import logging
import time
import requests
from functools import lru_cache

logger = logging.getLogger(__name__)

from src.constants import OPENROUTER_API_KEY
from src.genai.client import AIClient
from src.genai.chat_response import ChatResponse, ToolCall

FALLBACK_MODEL = "cognitivecomputations/dolphin3.0-r1-mistral-24b:free"
MAX_RETRIES = 2
RETRY_DELAY_S = 2


class OpenRouterClient(AIClient):
    """OpenRouter implementation of chat API."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _request(self, body: dict) -> dict:
        """Send a single request to the OpenRouter API."""
        raw = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(body),
        )
        return raw.json()

    def _parse_response(self, data: dict) -> ChatResponse:
        """Parse an OpenRouter response into a ChatResponse."""
        choices = data.get("choices")
        if not choices:
            raise RuntimeError(f"OpenRouter returned no choices: {data}")

        message = choices[0]["message"]
        content = message.get("content")
        tool_calls: list[ToolCall] = []

        for tc in message.get("tool_calls") or []:
            args = tc["function"]["arguments"]
            tool_calls.append(
                ToolCall(
                    id=tc["id"],
                    name=tc["function"]["name"],
                    arguments=json.loads(args) if isinstance(args, str) else args,
                )
            )

        return ChatResponse(content=content, tool_calls=tool_calls)

    def _is_rate_limit(self, data: dict) -> bool:
        """Check if the response is a rate-limit error."""
        error = data.get("error")
        if not error:
            return False
        code = error.get("code") if isinstance(error, dict) else None
        return code == 429

    def chat(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> ChatResponse:
        """
        Send a chat request to OpenRouter with automatic fallback.

        On a 429 rate-limit error, retries with FALLBACK_MODEL up to
        MAX_RETRIES times before raising.
        """
        if not model:
            raise ValueError("Model is required.")
        if not messages:
            raise ValueError("messages cannot be empty")

        body: dict = {
            "model": model,
            "messages": messages,
        }

        if tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["input_schema"],
                    },
                }
                for t in tools
            ]

        data = self._request(body)

        if not self._is_rate_limit(data):
            if "error" in data:
                logger.error("OpenRouter error: %s", json.dumps(data, default=str))
                error = data["error"]
                msg = error.get("message", error) if isinstance(error, dict) else error
                raise RuntimeError(f"OpenRouter API error: {msg}")
            return self._parse_response(data)

        # Rate-limited — retry with fallback model
        raw_meta = data["error"].get("metadata", {}).get("raw", "")
        logger.warning(
            "Rate-limited on '%s' (%s). Falling back to '%s'",
            model, raw_meta, FALLBACK_MODEL,
        )

        body["model"] = FALLBACK_MODEL
        for attempt in range(1, MAX_RETRIES + 1):
            time.sleep(RETRY_DELAY_S)
            logger.info("Retry %d/%d with fallback model '%s'", attempt, MAX_RETRIES, FALLBACK_MODEL)
            data = self._request(body)

            if not self._is_rate_limit(data):
                if "error" in data:
                    logger.error("OpenRouter error: %s", json.dumps(data, default=str))
                    error = data["error"]
                    msg = error.get("message", error) if isinstance(error, dict) else error
                    raise RuntimeError(f"OpenRouter API error: {msg}")
                logger.info("Fallback model '%s' responded successfully", FALLBACK_MODEL)
                return self._parse_response(data)

            logger.warning("Retry %d/%d also rate-limited", attempt, MAX_RETRIES)

        raise RuntimeError(
            f"OpenRouter rate-limited on both '{model}' and fallback '{FALLBACK_MODEL}'"
        )


@lru_cache(maxsize=1)
def get_openrouter_client() -> OpenRouterClient:
    """
    Return a cached OpenRouter client instance.

    Returns
    -------
    OpenRouterClient
        Singleton-like cached client configured from app constants.
    """
    return OpenRouterClient(api_key=OPENROUTER_API_KEY)
