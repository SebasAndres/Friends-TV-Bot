from __future__ import annotations

from src.genai.chat_response import ChatResponse, ToolCall, VirtualTool
from src.genai.model_facade import AIModelFacade
from src.genai.providers import Provider
from tests.conftest import MockAIClient, MockMCPManager


def _make_facade(client: MockAIClient) -> AIModelFacade:
    """Build a facade with a mock client injected."""
    facade = object.__new__(AIModelFacade)
    facade.model = "test-model"
    facade.provider = Provider.OLLAMA
    facade.system_prompt = "You are a test assistant."
    facade.max_tool_rounds = 5
    facade._virtual_tools = {}
    facade.history = [{"role": "system", "content": facade.system_prompt}]
    facade.client = client
    return facade


class TestNoToolCalls:
    def test_single_response(self) -> None:
        client = MockAIClient([ChatResponse(content="Hello!")])
        facade = _make_facade(client)

        result = facade.generate_response("Hi")

        assert result == "Hello!"
        assert len(client.calls) == 1
        assert facade.history[-1] == {"role": "assistant", "content": "Hello!"}
        assert facade.history[-2] == {"role": "user", "content": "Hi"}


class TestWithToolCalls:
    def test_one_tool_round(self) -> None:
        tool_call = ToolCall(id="tc1", name="read_file", arguments={"path": "/tmp/test"})
        responses = [
            ChatResponse(content=None, tool_calls=[tool_call]),
            ChatResponse(content="File says: hello"),
        ]
        client = MockAIClient(responses)
        mcp = MockMCPManager(tool_results={"read_file": "hello"})
        facade = _make_facade(client)

        result = facade.generate_response("Read the file", mcp_manager=mcp)

        assert result == "File says: hello"
        assert len(client.calls) == 2
        assert len(mcp.calls) == 1
        assert mcp.calls[0] == ("read_file", {"path": "/tmp/test"})

    def test_max_rounds_respected(self) -> None:
        tool_call = ToolCall(id="tc1", name="read_file", arguments={})
        always_tool = ChatResponse(content=None, tool_calls=[tool_call])
        final = ChatResponse(content="Done after max rounds")

        client = MockAIClient([always_tool] * 10 + [final])
        mcp = MockMCPManager(tool_results={"read_file": "data"})
        facade = _make_facade(client)
        facade.max_tool_rounds = 3

        result = facade.generate_response("Do work", mcp_manager=mcp)

        assert len(client.calls) == 3


class TestToolCallDenial:
    def test_denied_tool_returns_denial_message(self) -> None:
        tool_call = ToolCall(id="tc1", name="delete_file", arguments={"path": "/"})
        responses = [
            ChatResponse(content=None, tool_calls=[tool_call]),
            ChatResponse(content="Okay, I won't delete it."),
        ]
        client = MockAIClient(responses)
        mcp = MockMCPManager(tool_results={"delete_file": "deleted"})
        facade = _make_facade(client)

        def deny_all(name: str, args: dict) -> bool:
            return False

        result = facade.generate_response(
            "Delete everything",
            mcp_manager=mcp,
            on_tool_call=deny_all,
        )

        assert result == "Okay, I won't delete it."
        assert len(mcp.calls) == 0


class TestToolCallCache:
    def test_duplicate_calls_cached(self) -> None:
        tool_call = ToolCall(id="tc1", name="read_file", arguments={"path": "a.txt"})
        tool_call_dup = ToolCall(id="tc2", name="read_file", arguments={"path": "a.txt"})
        responses = [
            ChatResponse(content=None, tool_calls=[tool_call, tool_call_dup]),
            ChatResponse(content="Got it."),
        ]
        client = MockAIClient(responses)
        mcp = MockMCPManager(tool_results={"read_file": "content"})
        facade = _make_facade(client)

        result = facade.generate_response("Read a.txt twice", mcp_manager=mcp)

        assert result == "Got it."
        assert len(mcp.calls) == 1


class TestVirtualTools:
    def test_register_and_invoke(self) -> None:
        """Virtual tools are called instead of MCP."""
        tool_call = ToolCall(id="tc1", name="get_time", arguments={})
        responses = [
            ChatResponse(content=None, tool_calls=[tool_call]),
            ChatResponse(content="It is noon."),
        ]
        client = MockAIClient(responses)
        facade = _make_facade(client)

        facade.register_tool(VirtualTool(
            name="get_time",
            description="Get the current time.",
            input_schema={"type": "object", "properties": {}, "required": []},
            handler=lambda args: "12:00:00",
        ))

        result = facade.generate_response("What time is it?")

        assert result == "It is noon."
        # The tool definition should appear in the client call
        sent_tools = client.calls[0]["tools"]
        assert any(t["name"] == "get_time" for t in sent_tools)

    def test_virtual_tool_definitions_merged_with_mcp(self) -> None:
        """Virtual and MCP tools both appear in the tools list."""
        client = MockAIClient([ChatResponse(content="Hi")])
        mcp = MockMCPManager(tool_results={"read_file": "data"})
        facade = _make_facade(client)

        facade.register_tool(VirtualTool(
            name="my_tool",
            description="A custom tool.",
            input_schema={"type": "object", "properties": {}},
            handler=lambda args: "ok",
        ))

        facade.generate_response("Hello", mcp_manager=mcp)

        sent_tools = client.calls[0]["tools"]
        tool_names = {t["name"] for t in sent_tools}
        assert "read_file" in tool_names  # MCP
        assert "my_tool" in tool_names    # Virtual

    def test_unregister_tool(self) -> None:
        client = MockAIClient([ChatResponse(content="Hi")])
        facade = _make_facade(client)

        facade.register_tool(VirtualTool(
            name="temp_tool",
            description="Temporary.",
            input_schema={"type": "object", "properties": {}},
            handler=lambda args: "ok",
        ))
        facade.unregister_tool("temp_tool")
        facade.generate_response("Hello")

        sent_tools = client.calls[0]["tools"]
        assert sent_tools is None


class TestHistoryManagement:
    def test_history_appended_correctly(self) -> None:
        client = MockAIClient([ChatResponse(content="Reply")])
        facade = _make_facade(client)

        facade.generate_response("Question")

        assert len(facade.history) == 3
        assert facade.history[0]["role"] == "system"
        assert facade.history[1]["role"] == "user"
        assert facade.history[2]["role"] == "assistant"

    def test_skill_instructions_not_persisted(self) -> None:
        client = MockAIClient([ChatResponse(content="Done")])
        facade = _make_facade(client)

        facade.generate_response("Do it", skill_instructions="Special instructions")

        contents = [m["content"] for m in facade.history]
        assert not any("skill" in c for c in contents)
