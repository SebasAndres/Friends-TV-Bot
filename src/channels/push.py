"""Direct push messaging to channel platforms via their HTTP APIs."""

from __future__ import annotations

from logging import getLogger

import httpx

logger = getLogger(__name__)


def push_telegram(token: str, chat_id: int | str, message: str) -> bool:
    """Send a message directly via the Telegram Bot API.

    Returns True on success, False on failure.
    """
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception:
        logger.warning("Failed to push to Telegram chat %s", chat_id, exc_info=True)
        return False


def push_discord(token: str, channel_id: int | str, message: str) -> bool:
    """Send a message directly via the Discord REST API.

    Returns True on success, False on failure.
    """
    try:
        resp = httpx.post(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers={"Authorization": f"Bot {token}"},
            json={"content": message[:2000]},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception:
        logger.warning("Failed to push to Discord channel %s", channel_id, exc_info=True)
        return False


def push_message(channel_target: str, message: str) -> bool:
    """Dispatch a push message to a channel target string.

    Target format: ``"telegram:<chat_id>"`` or ``"discord:<channel_id>"``.
    Tokens are loaded from environment constants.
    """
    from src.constants import TELEGRAM_BOT_TOKEN, DISCORD_BOT_TOKEN

    if ":" not in channel_target:
        logger.warning("Invalid channel target format: %s", channel_target)
        return False

    platform, _, target_id = channel_target.partition(":")

    if platform == "telegram":
        if not TELEGRAM_BOT_TOKEN:
            logger.warning("Cannot push to Telegram: no bot token configured")
            return False
        return push_telegram(TELEGRAM_BOT_TOKEN, target_id, message)
    elif platform == "discord":
        if not DISCORD_BOT_TOKEN:
            logger.warning("Cannot push to Discord: no bot token configured")
            return False
        return push_discord(DISCORD_BOT_TOKEN, target_id, message)
    else:
        logger.warning("Unsupported push platform: %s", platform)
        return False
