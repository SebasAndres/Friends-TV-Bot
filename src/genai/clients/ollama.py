import json
from functools import lru_cache
from logging import getLogger

import httpx
import numpy as np
from ollama import Client

from src.constants import OLLAMA_HOST
from src.genai import AIClient
from src.genai.chat_response import ChatResponse, ToolCall
from src.genai.clients import retry_on_transient

logger = getLogger(__name__)


class OllamaClient(AIClient):
    """Ollama implementation of chat and embedding APIs."""

    tool_arguments_as_dict: bool = True

    def __init__(self, host: str):
        """
        Create an Ollama client wrapper.

        Parameters
        ----------
        host : str
            Base URL of the running Ollama server.

        Returns
        -------
        None
            Initializes the underlying Ollama SDK client.
        """
        if not host:
            raise ValueError("Ollama host is required.")
        self.host = host.rstrip("/")
        self.client = Client(host=host, timeout=600)

    @retry_on_transient()
    def chat(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> ChatResponse:
        """
        Send a chat request to Ollama.

        Parameters
        ----------
        model : str
            Ollama model name used for generation.
        messages : list[dict]
            Message list in role/content format.
        tools : list[dict] | None
            Optional MCP tool definitions.

        Returns
        -------
        ChatResponse
            Structured response with optional tool calls.
        """
        if not model:
            raise ValueError("Model is required.")
        if not messages:
            raise ValueError("messages cannot be empty")

        ollama_tools = None
        if tools:
            ollama_tools = [
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

        if ollama_tools:
            return self._chat_raw(model, messages, ollama_tools)

        try:
            response = self.client.chat(model=model, messages=messages)
            return ChatResponse(
                content=response.message.content or None,
                tool_calls=[],
            )
        except Exception as e:
            logger.error("Ollama chat error: %s", e)
            raise

    def _chat_raw(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict],
    ) -> ChatResponse:
        """Call Ollama chat API via raw HTTP to handle string tool args."""
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False,
        }
        resp = httpx.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=600,
        )
        resp.raise_for_status()
        data = resp.json()
        msg = data.get("message", {})
        content = msg.get("content") or None

        tool_calls: list[ToolCall] = []
        for tc in msg.get("tool_calls", []):
            func = tc.get("function", {})
            args = func.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            tool_calls.append(
                ToolCall(
                    id=f"call_{id(tc)}",
                    name=func.get("name", ""),
                    arguments=args,
                )
            )

        return ChatResponse(content=content, tool_calls=tool_calls)

    def embed(self, model: str, texts: list[str]) -> np.ndarray:
        """
        Generate embeddings through Ollama.

        Parameters
        ----------
        model : str
            Ollama embedding model name.
        texts : list[str]
            Input texts to embed.

        Returns
        -------
        numpy.ndarray
            Embedding matrix with shape ``(len(texts), embedding_dim)``.
        """
        if not model:
            raise ValueError("Embedding model is required.")
        if not texts:
            raise ValueError("texts cannot be empty")

        response = self.client.embed(model=model, input=texts)
        embeddings = getattr(response, "embeddings", None)
        if embeddings is None and isinstance(response, dict):
            embeddings = response.get("embeddings")
        if not embeddings:
            raise ValueError("Invalid Ollama embedding response: missing embeddings field.")

        return np.asarray(embeddings, dtype=np.float32)

@lru_cache(maxsize=1)
def get_ollama_client() -> OllamaClient:
    """
    Return a cached Ollama client instance.

    Returns
    -------
    OllamaClient
        Singleton-like cached client configured from app constants.
    """
    return OllamaClient(host=OLLAMA_HOST)
