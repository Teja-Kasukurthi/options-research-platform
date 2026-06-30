"""Telegram notifications via python-telegram-bot."""

import structlog
from telegram import Bot
from telegram.error import TelegramError

from app.core.config import settings

logger = structlog.get_logger(__name__)

_bot: Bot | None = None


def get_bot() -> Bot | None:
    global _bot
    if not settings.telegram_bot_token:
        return None
    if _bot is None:
        _bot = Bot(token=settings.telegram_bot_token)
    return _bot


async def send_alert(message: str, parse_mode: str = "Markdown") -> bool:
    bot = get_bot()
    if not bot or not settings.telegram_chat_id:
        logger.debug("telegram_not_configured")
        return False
    try:
        await bot.send_message(
            chat_id=settings.telegram_chat_id,
            text=message,
            parse_mode=parse_mode,
        )
        return True
    except TelegramError as e:
        logger.error("telegram_send_error", error=str(e))
        return False


async def send_signal_alert(signal: dict) -> None:
    msg = (
        f"*New Signal* 📊\n"
        f"Strategy: `{signal.get('strategy_type', 'unknown')}`\n"
        f"Score: `{signal.get('score', 0):.2f}`\n"
        f"Confidence: `{signal.get('confidence', 0):.0%}`\n"
    )
    await send_alert(msg)


async def send_stop_loss_alert(trade_id: str, symbol: str, ltp: float, stop_loss: float) -> None:
    msg = (
        f"*⚠️ Stop Loss Hit*\n"
        f"Symbol: `{symbol}`\n"
        f"LTP: `{ltp:.2f}`\n"
        f"Stop Loss: `{stop_loss:.2f}`\n"
        f"Trade ID: `{trade_id}`"
    )
    await send_alert(msg)
