"""Messaging channel abstractions."""

from src.channels.base import Channel
from src.channels.cli import CLIChannel
from src.channels.telegram import TelegramChannel

__all__ = ["Channel", "CLIChannel", "TelegramChannel", "CHANNEL_REGISTRY"]


def _build_registry() -> dict[str, type[Channel]]:
    """Build registry with available channels, skipping missing optional deps."""
    registry: dict[str, type[Channel]] = {
        "cli": CLIChannel,
        "telegram": TelegramChannel,
    }
    try:
        from src.channels.discord import DiscordChannel
        registry["discord"] = DiscordChannel
    except ImportError:
        pass
    return registry


CHANNEL_REGISTRY: dict[str, type[Channel]] = _build_registry()
