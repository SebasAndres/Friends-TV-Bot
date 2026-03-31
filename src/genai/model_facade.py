from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from logging import getLogger
from typing import TYPE_CHECKING, Callable

from src.genai.chat_response import VirtualTool
from src.genai.providers import Provider

if TYPE_CHECKING:
    from src.mcp.manager import MCPManager

logger = getLogger(__name__)

MAX_TOOL_ROUNDS = 5


class AIModelFacade:
    """Facade around provider-specific AI clients for chat interactions."""

    def __init__(
        self,
        provider: Provider,
        model: str,
        system_prompt: str,
        history: list[dict[str, str]],
    ) -> None:
        self.model = model
        self.provider = provider
        self.system_prompt = system_prompt
        self.max_tool_rounds = MAX_TOOL_ROUNDS
        self._virtual_tools: dict[str, VirtualTool] = {}
        self.history: list[dict] = [
            {"role": "system", "content": self.system_prompt},
            *history,
        ]
        self._setup_client(provider)

    def register_tool(self, tool: VirtualTool) -> None:
        """Register a local tool the model can invoke."""
        self._virtual_tools[tool.name] = tool

    def unregister_tool(self, name: str) -> None:
        """Remove a previously registered virtual tool."""
        self._virtual_tools.pop(name, None)

    def _setup_client(self, provider: Provider) -> None:
        if provider == Provider.OLLAMA:
            from src.genai.clients.ollama import get_ollama_client
            self.client = get_ollama_client()
        elif provider == Provider.GEMINI:
            from src.genai.clients.gemini import get_gemini_client
            self.client = get_gemini_client()
        elif provider == Provider.OPEN_ROUTER:
            from src.genai.clients.openrouter import get_openrouter_client
            self.client = get_openrouter_client()
        elif provider == Provider.VLLM:
            from src.genai.clients.vllm import get_vllm_client
            self.client = get_vllm_client()
        elif provider == Provider.ANTHROPIC:
            from src.genai.clients.anthropic import get_anthropic_client
            self.client = get_anthropic_client()
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def add_to_history(self, role: str, content: str) -> None:
        """Append a message to the conversation history."""
        self.history.append({"role": role, "content": content})

    def generate_response(
        self,
        user_message: str,
        mcp_manager: MCPManager | None = None,
        on_tool_call: Callable[[str, dict], bool] | None = None,
        skill_instructions: str | None = None,
    ) -> str:
        """Generate a response, letting the model call tools as needed.

        Parameters
        ----------
        user_message : str
            The message from the user to respond to.
        mcp_manager : MCPManager or None
            MCP manager providing tool definitions and execution.
        on_tool_call : callable or None
            Callback ``(tool_name, arguments) -> bool`` for tool approval.
        skill_instructions : str or None
            Skill-specific instructions injected into the prompt for this turn.
        """
        messages = self._build_turn_messages(user_message, skill_instructions)
        tools = self._collect_tool_definitions(mcp_manager)
        tool_messages: list[dict] = []

        try:
            content = self._run_tool_loop(
                messages, tool_messages, tools, mcp_manager, on_tool_call,
            )
        except Exception as e:
            logger.error("AI provider error (%s): %s", self.provider, e)
            content = f"⚠ AI provider error: {e}"

        self.history.append({"role": "user", "content": user_message})
        self.history.extend(tool_messages)
        self.history.append({"role": "assistant", "content": content})
        return content

    def _build_turn_messages(
        self,
        user_message: str,
        skill_instructions: str | None,
    ) -> list[dict]:
        """Build the message list for a single turn.

        Copies the current history and appends the user message.
        Skill instructions are injected as a temporary system message.
        """
        messages: list[dict] = list(self.history)
        if skill_instructions:
            messages.append({
                "role": "system",
                "content": f"[skill]\n{skill_instructions}",
            })
        messages.append({"role": "user", "content": user_message})
        return messages

    def _collect_tool_definitions(
        self, mcp_manager: MCPManager | None,
    ) -> list[dict] | None:
        """Merge MCP and virtual tool definitions into a single list."""
        mcp_tools = mcp_manager.get_tools() if mcp_manager else []
        vtool_defs = [vt.definition for vt in self._virtual_tools.values()]
        combined = mcp_tools + vtool_defs
        return combined or None

    def _run_tool_loop(
        self,
        messages: list[dict],
        tool_messages: list[dict],
        tools: list[dict] | None,
        mcp_manager: MCPManager | None,
        on_tool_call: Callable[[str, dict], bool] | None,
    ) -> str:
        """Chat with the model, executing tool calls up to MAX_TOOL_ROUNDS."""
        response = None
        tool_cache: dict[tuple[str, str], str] = {}

        for _ in range(self.max_tool_rounds):
            response = self.client.chat(
                model=self.model, messages=messages, tools=tools,
            )
            if not response.has_tool_calls:
                break
            self._process_tool_round(
                response, messages, tool_messages, tool_cache,
                mcp_manager, on_tool_call,
            )

        content = response.content if response else None
        if not content:
            raise ValueError("Received empty response from the AI model.")
        return content

    def _build_tool_call_msg(self, response: object) -> dict:
        args_as_dict = self.client.tool_arguments_as_dict
        return {
            "role": "assistant",
            "content": response.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": tc.arguments if args_as_dict else json.dumps(tc.arguments),
                    },
                }
                for tc in response.tool_calls
            ],
        }

    def _exec_tool_call(
        self,
        tc: object,
        tool_cache: dict[tuple[str, str], str],
        mcp_manager: MCPManager | None,
        on_tool_call: Callable[[str, dict], bool] | None,
    ) -> tuple[object, str]:
        if on_tool_call and not on_tool_call(tc.name, tc.arguments):
            return tc, "Tool call denied by user."
        cache_key = (tc.name, json.dumps(tc.arguments, sort_keys=True))
        if cache_key in tool_cache:
            return tc, tool_cache[cache_key]
        try:
            result = self._execute_tool(tc, mcp_manager)
            result = result if isinstance(result, str) else str(result)
            tool_cache[cache_key] = result
            return tc, result
        except Exception as e:
            logger.warning("Tool call %s failed: %s", tc.name, e)
            return tc, f"Error: tool '{tc.name}' failed: {e}"

    def _process_tool_round(
        self,
        response: object,
        messages: list[dict],
        tool_messages: list[dict],
        tool_cache: dict[tuple[str, str], str],
        mcp_manager: MCPManager | None,
        on_tool_call: Callable[[str, dict], bool] | None,
    ) -> None:
        tool_call_msg = self._build_tool_call_msg(response)
        messages.append(tool_call_msg)
        tool_messages.append(tool_call_msg)

        exec_fn = lambda tc: self._exec_tool_call(tc, tool_cache, mcp_manager, on_tool_call)
        sequential = on_tool_call is not None and len(response.tool_calls) > 1
        if sequential:
            results = [exec_fn(tc) for tc in response.tool_calls]
        else:
            with ThreadPoolExecutor(max_workers=len(response.tool_calls)) as pool:
                results = list(pool.map(exec_fn, response.tool_calls))

        for tc, result in results:
            tool_result_msg = {
                "role": "tool",
                "tool_call_id": tc.id,
                "name": tc.name,
                "content": result,
            }
            messages.append(tool_result_msg)
            tool_messages.append(tool_result_msg)

    def _execute_tool(
        self, tc: object, mcp_manager: MCPManager | None,
    ) -> str:
        """Dispatch a single tool call to virtual tool or MCP."""
        if tc.name in self._virtual_tools:
            return self._virtual_tools[tc.name].handler(tc.arguments)
        if mcp_manager:
            return mcp_manager.call_tool(tc.name, tc.arguments)
        raise ValueError(f"Unknown tool: {tc.name}")
