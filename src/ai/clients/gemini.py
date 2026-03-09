from functools import lru_cache
import os
import numpy as np

from src.ai import AIClient


class GeminiClient(AIClient):
    """Gemini implementation of chat and embedding APIs."""

    def __init__(self, api_key: str | None = None):
        """
        Create a Gemini client wrapper.

        Parameters
        ----------
        api_key : str | None, optional
            Google API key. If omitted, ``GOOGLE_API_KEY`` is used.

        Returns
        -------
        None
            Initializes the underlying Gemini SDK client.
        """
        from google import genai

        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is required to use Gemini.")

        self.genai = genai
        self.client = genai.Client(api_key=self.api_key)


    def chat(self, model: str, messages: list[dict[str, str]]) -> str:
        """
        Send a chat request to Gemini.

        Parameters
        ----------
        model : str
            Gemini model name used for generation.
        messages : list[dict[str, str]]
            Message list in role/content format.

        Returns
        -------
        str
            Assistant text response.
        """
        if not messages:
            raise ValueError("messages cannot be empty")

        system_instruction = None
        contents = []

        for message in messages:
            role = (message.get("role") or "").strip()
            content = (message.get("content") or "").strip()
            if not content:
                continue

            if role == "system":
                if system_instruction is None:
                    system_instruction = content
                else:
                    system_instruction += f"\n\n{content}"
                continue

            mapped_role = "model" if role == "assistant" else "user"
            contents.append(
                self.genai.types.Content(
                    role=mapped_role,
                    parts=[self.genai.types.Part(text=content)]
                )
            )

        if not contents:
            raise ValueError("No user/assistant content found in messages.")

        config = None
        if system_instruction:
            config = self.genai.types.GenerateContentConfig(
                system_instruction=system_instruction
            )

        response = self.client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )

        text = (response.text or "").strip()
        if text:
            return text

        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            candidate_content = getattr(candidate, "content", None)
            parts = getattr(candidate_content, "parts", None) or []
            joined = "".join(
                part.text for part in parts
                if getattr(part, "text", None)
            ).strip()
            if joined:
                return joined

        return ""

    def embed(self, model: str, texts: list[str]) -> np.ndarray:
        """
        Generate embeddings through Gemini.

        Parameters
        ----------
        model : str
            Gemini embedding model name.
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

        response = self.client.models.embed_content(
            model=model,
            contents=texts,
        )
        embeddings = getattr(response, "embeddings", None)
        if embeddings is None and isinstance(response, dict):
            embeddings = response.get("embeddings")
        if not embeddings:
            raise ValueError("Invalid Gemini embedding response: missing embeddings field.")

        vectors: list[list[float]] = []
        for emb in embeddings:
            values = getattr(emb, "values", None)
            if values is None and isinstance(emb, dict):
                values = emb.get("values")
            if values is None:
                raise ValueError("Invalid Gemini embedding response: missing values field.")
            vectors.append(list(values))

        return np.asarray(vectors, dtype=np.float32)

@lru_cache(maxsize=1)
def get_gemini_client() -> GeminiClient:
    """
    Return a cached Gemini client instance.

    Returns
    -------
    GeminiClient
        Singleton-like cached client configured from environment variables.
    """
    return GeminiClient()
