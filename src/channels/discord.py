"""Discord channel implementation."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from src.channels.base import Channel
from src.daemon.client import DaemonClient

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 2000


class DiscordChannel(Channel):
    """Discord bot channel that bridges Discord messages to the daemon."""

    def __init__(self, token: str, client: DaemonClient | None = None) -> None:
        super().__init__(client)
        if not token:
            raise ValueError("DISCORD_BOT_TOKEN not set. Add it to your .env file.")
        self._token = token
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._sessions: dict[int, str] = {}
        self._meta: dict[int, dict] = {}

    def start(self) -> None:
        """Build the Discord bot and run it (blocking)."""
        import discord

        self.ensure_daemon()
        self._setup_logging()

        intents = discord.Intents.default()
        intents.message_content = True
        bot = discord.Client(intents=intents)
        tree = discord.app_commands.CommandTree(bot)
        self._bot = bot

        @bot.event
        async def on_ready() -> None:
            logger.info("Discord bot ready as %s", bot.user)
            await tree.sync()

        @bot.event
        async def on_message(message: discord.Message) -> None:
            if message.author == bot.user:
                return
            if message.content.startswith("/change"):
                await self._cmd_change(message)
                return
            if not message.content:
                return
            await self._handle_message(message)

        @tree.command(name="change", description="Switch to a new random character")
        async def slash_change(interaction: discord.Interaction) -> None:
            channel_id = interaction.channel_id
            old_sid = self._sessions.pop(channel_id, None)
            if old_sid:
                self.client.delete_session(old_sid)
            self._meta.pop(channel_id, None)
            self._ensure_session(channel_id)
            meta = self._meta[channel_id]
            await interaction.response.send_message(
                f"New character: {meta['emoji']} **{meta['name']}**\n\n{meta['hi_message']}"
            )

        logger.info("Discord bot starting (daemon mode)...")
        bot.run(self._token, log_handler=None)

    def stop(self) -> None:
        """Signal the bot to stop."""
        if hasattr(self, "_bot") and self._bot:
            import asyncio
            asyncio.get_event_loop().create_task(self._bot.close())
        self._executor.shutdown(wait=False)

    def _ensure_session(self, channel_id: int) -> str:
        """Return session_id for this channel, creating one if needed."""
        if channel_id not in self._sessions:
            session = self.client.create_session()
            self._sessions[channel_id] = session.id
            self._meta[channel_id] = {
                "name": session.character_name,
                "emoji": session.emoji,
                "color": session.color,
                "hi_message": session.hi_message,
            }
        return self._sessions[channel_id]

    async def _handle_message(self, message: "discord.Message") -> None:
        """Handle a regular text message."""
        import asyncio

        channel_id = message.channel.id
        session_id = self._ensure_session(channel_id)

        async with message.channel.typing():
            loop = asyncio.get_running_loop()
            try:
                response, _ = await loop.run_in_executor(
                    self._executor,
                    partial(self.client.send_message, session_id, message.content),
                )
            except Exception:
                logger.exception("Error generating response")
                response = "Sorry, something went wrong."

        for i in range(0, len(response), MAX_MESSAGE_LENGTH):
            await message.channel.send(response[i : i + MAX_MESSAGE_LENGTH])

    async def _cmd_change(self, message: "discord.Message") -> None:
        """Handle the /change text command."""
        channel_id = message.channel.id
        old_sid = self._sessions.pop(channel_id, None)
        if old_sid:
            self.client.delete_session(old_sid)
        self._meta.pop(channel_id, None)

        self._ensure_session(channel_id)
        meta = self._meta[channel_id]
        await message.channel.send(
            f"New character: {meta['emoji']} **{meta['name']}**\n\n{meta['hi_message']}"
        )

    @staticmethod
    def _setup_logging() -> None:
        """Configure logging for the Discord bot process."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        )
        logging.getLogger("discord").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
