"""MCP client manager — connects to MCP servers and exposes their tools."""

from __future__ import annotations

import asyncio
import json
import os
import threading
from contextlib import AsyncExitStack
from functools import lru_cache
from logging import getLogger
from pathlib import Path

logger = getLogger(__name__)

_MCP_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "mcp_servers.json"


class MCPManager:
    """Sync wrapper around async MCP client sessions.

    Runs an asyncio event loop in a background thread so the rest of the
    (synchronous) application can call :meth:`get_tools` and :meth:`call_tool`
    without ``await``.
    """

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._exit_stack: AsyncExitStack | None = None
        self._sessions: dict[str, object] = {}
        self._tools: list[dict] = []
        self._tool_server_map: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public (sync) API
    # ------------------------------------------------------------------

    def connect(self, config_path: str) -> None:
        """Read *config_path* and connect to every MCP server listed there."""
        self._run_sync(self._connect_all(config_path))

    def get_tools(self) -> list[dict]:
        """Return tool definitions from all connected servers.

        Each dict has keys ``name``, ``description``, and ``input_schema``.
        """
        return self._tools

    def call_tool(self, name: str, arguments: dict) -> str:
        """Execute a tool by name and return the textual result."""
        return self._run_sync(self._call_tool_async(name, arguments))

    def close(self) -> None:
        """Shut down every server connection and stop the event loop."""
        if self._exit_stack:
            try:
                self._run_sync(self._exit_stack.aclose())
            except Exception:
                pass
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _run_sync(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=60)

    async def _connect_all(self, config_path: str) -> None:
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()

        with open(config_path) as fh:
            config: dict = json.load(fh)

        for server_name, server_cfg in config.items():
            try:
                await self._connect_one(
                    server_name, server_cfg, ClientSession, StdioServerParameters, stdio_client,
                )
            except Exception as exc:
                logger.warning("MCP server '%s' failed to connect: %s", server_name, exc)

    async def _connect_one(self, name, cfg, ClientSession, StdioServerParameters, stdio_client):
        resolved_env: dict[str, str] = {}
        for k, v in cfg.get("env", {}).items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                resolved_env[k] = os.environ.get(v[2:-1], "")
            else:
                resolved_env[k] = str(v)

        params = StdioServerParameters(
            command=cfg["command"],
            args=cfg.get("args", []),
            env={**os.environ, **resolved_env},
        )

        devnull = open(os.devnull, "w")
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(params, errlog=devnull)
        )
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()

        self._sessions[name] = session

        tools_result = await session.list_tools()
        for tool in tools_result.tools:
            self._tools.append({
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
            })
            self._tool_server_map[tool.name] = name

        logger.info(
            "MCP server '%s': %d tool(s) registered", name, len(tools_result.tools),
        )

    async def _call_tool_async(self, name: str, arguments: dict) -> str:
        server_name = self._tool_server_map.get(name)
        if not server_name or server_name not in self._sessions:
            return f"Error: tool '{name}' not available"

        session = self._sessions[server_name]
        result = await session.call_tool(name, arguments)

        texts: list[str] = []
        for block in result.content:
            if hasattr(block, "text"):
                texts.append(block.text)
        return "\n".join(texts) if texts else str(result.content)


@lru_cache(maxsize=1)
def get_mcp_manager() -> MCPManager | None:
    """Return a cached MCPManager singleton, or None if unavailable."""
    if not _MCP_CONFIG_PATH.exists():
        return None

    try:
        manager = MCPManager()
        manager.connect(str(_MCP_CONFIG_PATH))

        if manager.get_tools():
            tool_names = [t["name"] for t in manager.get_tools()]
            logger.info("MCP tools available: %s", ", ".join(tool_names))
            return manager

        manager.close()
        return None
    except Exception as exc:
        logger.warning("MCP initialization failed: %s", exc)
        return None
