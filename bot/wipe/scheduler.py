import asyncio
import logging

from data.models_wipe import (
    get_wipe_started_servers, mark_wipe_start_notified,
    get_wipe_soon_servers, mark_wipe_1h_notified,
)
from data.models_notifications import is_notif_enabled
from bot.utils.message_queue import mq

logger = logging.getLogger(__name__)


async def _check_wipe_starts():
    for s in await get_wipe_started_servers():
        if await is_notif_enabled(s["user_id"], "wipe_start"):
            await mq.send(
                s["user_id"],
                f"🧹 <b>Вайп начался!</b>\n\nСервер <b>{s['name']}</b> — таймер запущен.",
            )
        await mark_wipe_start_notified(s["id"])


async def _check_wipe_soon():
    for s in await get_wipe_soon_servers():
        if await is_notif_enabled(s["user_id"], "wipe_1h"):
            await mq.send(
                s["user_id"],
                f"⏰ <b>Вайп через 1 час!</b>\n\nСервер <b>{s['name']}</b> — готовься.",
            )
        await mark_wipe_1h_notified(s["id"])


async def wipe_scheduler():
    while True:
        await asyncio.sleep(60)
        try:
            await _check_wipe_starts()
            await _check_wipe_soon()
        except Exception as e:
            logger.error("Ошибка в wipe_scheduler: %s", e)
