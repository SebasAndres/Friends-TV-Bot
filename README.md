# friends-bot

A terminal chatbot where you talk to characters from the TV show Friends. Each character has their own personality, catchphrases, and style.

## Characters

| Emoji | Character | Personality |
|-------|-----------|-------------|
| 🍕 | Joey Tribbiani | Food-loving, loyal, "How you doin'?" |
| 👩‍🍳 | Monica Geller | Competitive, organized, amazing cook |
| 🦕 | Ross Geller | Paleontologist, intellectual, "We were on a break!" |
| 😏 | Chandler Bing | Sarcastic, "Could this BE any more..." |
| 🎸 | Phoebe Buffay | Quirky, free-spirited, "Smelly Cat" musician |

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

### Environment Variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Only for Gemini | Your [Google AI API key](https://aistudio.google.com/apikey). Not needed if using Ollama. |

### LLM Provider

The bot supports two providers, configured in `src/constants.py`:

**Ollama (default)** — runs locally, no API key needed:

```bash
ollama pull qwen2:1.5b
```

**Gemini** — requires a `GOOGLE_API_KEY` in your `.env`:

```python
# src/constants.py
MODEL_PROVIDER = "gemini"
MODEL = "gemini-2.0-flash"
```

## Usage

```bash
uv run python main.py
```

A random character will greet you. Type your messages and chat with them. Type `/exit` or `/quit` to leave.

## Project Structure

```
main.py                          # Entry point
src/
  agents/
    agent.py                     # Base Agent class
    agent_manager.py             # Random agent selection
    characters/
      joey.py                    # Joey Tribbiani
      monica.py                  # Monica Geller
      ross.py                    # Ross Geller
      chandler.py                # Chandler Bing
      phoebe.py                  # Phoebe Buffay
  ai/
    model_facade.py              # LLM abstraction layer
    clients/
      ollama.py                  # Ollama client
  display.py                     # Rich terminal UI
```