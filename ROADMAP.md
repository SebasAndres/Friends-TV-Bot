# Qubito Roadmap — Toward an OpenClaw-like Architecture

> Goal: Transform Qubito from an interactive CLI chat into a **persistent background agent**
> that connects to multiple messaging channels and acts autonomously on your behalf.

---

## Phase 0 — Stabilize the Foundation

_Priority: things that are stubbed or broken today._

- [x] **Conversation persistence** — SQLite-backed `ConversationDB` at `~/.qubito/qubito.db`. Sessions and messages persist across daemon restarts. `Agent._load_recent_conversations()` loads from DB when available.
- [x] **PDF extraction** — implemented via `pymupdf` in `src/files.py`. The `/load` handler supports PDF, images (OCR), and plain text.
- [x] **Test suite** — 51 tests covering config resolution, character loading, skill registry, tool-call loop, conversation DB, and event bus. pytest with dev dependencies.
- [x] **Error resilience** — Timeouts on MCP tool calls (30s), provider HTTP calls (60-120s). Retry decorator for Ollama/Gemini on transient errors. Graceful tool failure handling in model facade. MCP server crash recovery with auto-reconnect.

---

## Phase 1 — Background Daemon (the Gateway)

_This is the single biggest architectural shift. OpenClaw's core is a long-running gateway process._

- [x] **Daemon mode** (`qubito daemon start/stop/status/install/uninstall`)
  - Runs as `systemd --user` service (`qubito daemon install`). `Restart=on-failure` with 5s delay.
  - PID file at `~/.qubito/daemon.pid` + `/status` health-check endpoint.
- [x] **Event bus / message router**
  - Async `EventBus` with pub/sub in `src/bus/`. Emits `message.inbound` and `message.outbound` events from API endpoints.
  - Channels continue using HTTP; bus is additive infrastructure for Phase 2+ migration.
- [x] **Session manager**
  - In-memory `SessionManager` backed by SQLite persistence. Per-session conversation history.
  - Configurable idle timeout (`QUBITO_SESSION_TIMEOUT`, default 30min) with background eviction loop.
- [x] **Local API**
  - FastAPI on `127.0.0.1:8741`. Endpoints: `POST /message`, `POST /message/stream` (SSE), `GET/POST/DELETE /sessions`, `GET /status`, `GET /characters`.

---

## Phase 2 — Multi-Channel Support

_OpenClaw's killer feature is 25+ channel integrations. Start with high-value ones._

- [x] **Channel abstraction** — `Channel` ABC in `src/channels/base.py` with `start()`, `stop()`, `client: DaemonClient`.
- [x] **Refactor Telegram** — `TelegramChannel(Channel)` uses `DaemonClient` to communicate with daemon.
- [ ] **WhatsApp** — via WhatsApp Cloud API (webhook-based, runs inside daemon).
- [ ] **Discord** — discord.py bot connecting through the channel abstraction.
- [ ] **Slack** — Slack Bolt app as a channel.
- [ ] **Signal** — via signal-cli or signald.
- [ ] **WebChat** — simple web UI served by the local API (HTML + SSE).
- [x] **CLI** — `CLIChannel(Channel)` is a thin client that talks to the daemon API via `DaemonClient`.

---

## Phase 3 — Autonomous Agent Loop

_Move from "respond when asked" to "act on schedule and react to events."_

- [ ] **Cron / scheduled tasks**
  - `qubito cron add "every morning at 8am" "summarize my unread messages"`
  - Stored in config, executed by the daemon.
- [ ] **Webhooks**
  - HTTP endpoint on the local API that triggers agent actions.
  - GitHub webhook → "PR #42 was merged" → agent posts to Slack.
- [ ] **Proactive actions**
  - Agent can initiate messages (reminders, digests, alerts) without user prompt.
  - Configurable per-channel: opt-in to proactive messages.
- [ ] **Background tasks**
  - Long-running tasks (web research, file processing) that the agent works on asynchronously.
  - Status reporting: "I'm 60% done with your research task."

---

## Phase 4 — Multi-Agent Routing

_OpenClaw can route different channels/accounts to isolated agents._

- [ ] **Agent registry** — manage multiple named agents, each with its own character, tools, and RAG store.
- [ ] **Routing rules** — map channels/users to specific agents:
  - "Route my Telegram DMs to the work agent."
  - "Route the Discord #support channel to the support agent."
- [ ] **Agent-to-agent communication** — agents can delegate to or consult other agents.
- [ ] **Workspace isolation** — each agent gets its own conversation history, RAG index, and MCP server set.

---

## Phase 5 — Web Control UI

_OpenClaw ships a web-based control panel served by the gateway._

- [ ] **Dashboard** — agent status, active sessions, recent messages, system health.
- [ ] **Configuration UI** — manage agents, channels, skills, rules, cron jobs without editing files.
- [ ] **Chat UI** — WebChat interface for direct interaction (alternative to CLI).
- [ ] **Logs & observability** — searchable message history, tool call traces, error logs.
- [ ] **Tech**: lightweight framework (FastAPI + HTMX, or a small React/Svelte app).

---

## Phase 6 — Skills Platform

_Extend the current slash-command system into a proper skills marketplace._

- [ ] **Skill packaging** — skills as self-contained directories with dependencies, not just markdown files.
- [ ] **Skill tiers**: bundled (ships with Qubito), managed (installed from registry), workspace (project-local).
- [ ] **Skill discovery** — `qubito skill search "calendar"`, `qubito skill install <name>`.
- [ ] **Skill SDK** — documented API for third-party skill authors.
- [ ] **Permission model** — skills declare what they need (network, filesystem, channels) and users approve.

---

## Phase 7 — Companion Apps & Voice

_OpenClaw has macOS/iOS/Android companion apps with voice wake words._

- [ ] **Voice mode** — always-on microphone with wake word detection (extend existing STT).
- [ ] **TTS responses** — text-to-speech output for voice conversations.
- [ ] **Desktop tray app** — system tray icon with quick-chat popup (Electron or Tauri).
- [ ] **Mobile node** — lightweight app that connects to your daemon, forwards voice/camera.

---

## Phase 8 — Security & Privacy

- [ ] **DM pairing** — unknown senders must be approved before the agent responds (OpenClaw does this).
- [ ] **End-to-end encryption** for channel ↔ daemon communication.
- [ ] **Audit log** — immutable record of all agent actions for review.
- [ ] **Tool sandboxing** — MCP servers run in containers or with restricted permissions.
- [ ] **Auth for local API** — token-based auth so only authorized clients connect to the daemon.

---

## Suggested Execution Order

```
Now          Phase 0  — Stabilize (persistence, PDF, tests, error handling)
             Phase 1  — Daemon + local API (the architectural pivot)
             Phase 2  — Multi-channel (Telegram refactor, WhatsApp, Discord)
             Phase 3  — Cron, webhooks, proactive actions
Later        Phase 4  — Multi-agent routing
             Phase 5  — Web control UI
             Phase 6  — Skills platform
Eventually   Phase 7  — Companion apps & voice
             Phase 8  — Security hardening
```

Phases 0-2 are the critical path. Once Qubito runs as a daemon with a channel abstraction and local API, everything else layers on top naturally.

---

## Key Architectural Decisions to Make Early

| Decision | Options | OpenClaw's choice |
|----------|---------|-------------------|
| Daemon process manager | systemd user service vs supervisor vs custom | systemd/launchd |
| Internal messaging | asyncio queues vs Redis vs ZeroMQ | WebSocket-based |
| Local API protocol | HTTP REST vs WebSocket vs gRPC | WebSocket |
| Persistence | SQLite vs PostgreSQL vs JSON files | SQLite recommended for local-first |
| Web UI framework | FastAPI+HTMX vs Next.js vs Svelte | Node/React (OpenClaw is TS) |
| Channel subprocess model | In-process vs child process vs MCP server | In-process (OpenClaw) |
