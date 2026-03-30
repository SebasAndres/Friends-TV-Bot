"""Simple async pub/sub event bus for internal message routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from logging import getLogger
from typing import Awaitable, Callable

logger = getLogger(__name__)

Listener = Callable[["Event"], Awaitable[None]]


@dataclass
class Event:
    """A typed event flowing through the bus."""

    type: str
    session_id: str
    channel_id: str | None = None
    payload: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventBus:
    """Lightweight async event emitter for decoupling components."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[Listener]] = {}

    def on(self, event_type: str, listener: Listener) -> None:
        """Subscribe *listener* to events of *event_type*."""
        self._listeners.setdefault(event_type, []).append(listener)

    def off(self, event_type: str, listener: Listener) -> None:
        """Unsubscribe *listener* from *event_type*."""
        listeners = self._listeners.get(event_type, [])
        try:
            listeners.remove(listener)
        except ValueError:
            pass

    async def emit(self, event: Event) -> None:
        """Dispatch *event* to all matching listeners."""
        for listener in self._listeners.get(event.type, []):
            try:
                await listener(event)
            except Exception:
                logger.exception("Event listener error for %s", event.type)

    @property
    def listener_count(self) -> int:
        """Total number of registered listeners across all event types."""
        return sum(len(v) for v in self._listeners.values())
