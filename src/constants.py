"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

AI_CLIENT_PROVIDER = os.getenv("AI_CLIENT_PROVIDER")
AI_CLIENT_MODEL = os.getenv("AI_CLIENT_MODEL")

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", AI_CLIENT_PROVIDER).lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

