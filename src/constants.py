"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "ollama")
MODEL = os.getenv("MODEL", "qwen2:1.5b")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", MODEL_PROVIDER).lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "")
