# Qubito

A natural-language OS that runs as a background loop, executing commands through conversation. Search the web, run code, manage files, answer messages, create calendar events, and more — all through natural language, powered by LLM agents with configurable personalities.

## Characters

Agents respond through configurable character personalities defined as markdown files in `agents/`. Some examples are included out of the box.

## Setup Guide

### 1. Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- An LLM provider ([Ollama](https://ollama.com/), [Gemini](https://aistudio.google.com/), or [OpenRouter](https://openrouter.ai/))

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment

Copy the example file and edit it:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_CLIENT_PROVIDER` | `ollama` | LLM provider: `ollama`, `gemini`, or `openrouter` |
| `AI_CLIENT_MODEL` | `cogito:3b` | Model name (depends on the provider) |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL (only for `ollama`) |
| `EMBEDDING_PROVIDER` | `AI_CLIENT_PROVIDER` | Embedding backend: `ollama` or `gemini` |
| `EMBEDDING_MODEL` | provider default | Embedding model (e.g. `nomic-embed-text` or `text-embedding-004`) |
| `GOOGLE_API_KEY` | — | [Google AI API key](https://aistudio.google.com/apikey) (only for `gemini`) |
| `OPENROUTER_API_KEY` | — | [OpenRouter API key](https://openrouter.ai/) (only for `openrouter`) |

### 4. Set up your LLM provider

**Ollama (default)** — runs locally, no API key needed:

```bash
ollama pull qwen2:1.5b
ollama pull nomic-embed-text
```

**Gemini** — set these in your `.env`:

```
AI_CLIENT_PROVIDER=gemini
MODEL=gemini-2.0-flash
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=text-embedding-004
GOOGLE_API_KEY=your-api-key-here
```

### 5. (Optional) Create a shell alias

Add this to your `~/.bashrc` or `~/.zshrc` for quick access:

```bash
alias qubito='cd ~/my/qubito && uv run python main.py'
```

Then reload your shell:

```bash
source ~/.bashrc
```

## Usage

```bash
uv run python main.py
```

A random character will greet you. Type your messages and chat with them. Type `q`, `/exit`, or `/quit` to leave.

Commands:
- `/load <path>` — index a local text file for retrieval context
- `/context` or `/ctx` — inspect currently indexed chunks
- `/history` — print chat history
- `/lineup` — show available characters
- `/summarize` — summarize the conversation so far
- `/help` — list available commands