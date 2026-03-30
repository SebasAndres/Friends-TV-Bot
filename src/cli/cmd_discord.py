"""Handler for the ``qubito discord`` subcommand."""

from __future__ import annotations


def run_discord() -> None:
    """Start the Discord bot channel."""
    from src.constants import DISCORD_BOT_TOKEN
    from src.channels.discord import DiscordChannel

    channel = DiscordChannel(token=DISCORD_BOT_TOKEN)
    channel.start()
