from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolCall:
    """A single tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResponse:
    """Structured response from a chat completion that may include tool calls."""

    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


@dataclass
class VirtualTool:
    """A locally-defined tool the model can invoke without MCP."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., str]

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
