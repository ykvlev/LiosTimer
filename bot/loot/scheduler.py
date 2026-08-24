import asyncio
import logging

from data.models_loot import get_loot_ready_to_notify, increment_loot_notified, loot_notify_text
from data.models_clan_rooms import get_clan_rooms_ready_to_notify, increment_clan_loot_notified
from data.models_clan import get_clan_members
from data.models_notifications import is_notif_enabled
from bot.utils.message_queue import mq
from bot.keyboards.loot_menu import notify_loot_quick_kb

logger = logging.getLogger(__name__)


async def _send_and_mark(items: list[dict]):
    for item in items:
        if await is_notif_enabled(item["user_id"], "loot"):
            text = loot_notify_text(item["location"], item["slot"], item.get("card_type"))
            kb = notify_loot_quick_kb(item["location"], item["slot"])
            await mq.send(item["user_id"], text, reply_markup=kb)
        await increment_loot_notified(item["user_id"], item["location"], item["slot"])


async def _send_and_mark_clan(items: list[dict]):
    for item in items:
        clan_id  = item["clan_id"]
        location = item["location"]
        slot     = item["slot"]
        card_type = item.get("card_type")

        members = await get_clan_members(clan_id)
        text = loot_notify_text(location, slot, card_type)
        kb   = notify_loot_quick_kb(location, slot)

        for member in members:
            uid = member["user_id"]
            if await is_notif_enabled(uid, "loot"):
                await mq.send(uid, text, reply_markup=kb)

        await increment_clan_loot_notified(clan_id, location, slot)


async def loot_scheduler():
    while True:
        await asyncio.sleep(60)
        try:
            first, second = await get_loot_ready_to_notify()
            await _send_and_mark(first)
            await _send_and_mark(second)

            clan_first, clan_second = await get_clan_rooms_ready_to_notify()
            await _send_and_mark_clan(clan_first)
            await _send_and_mark_clan(clan_second)
        except Exception as e:
            logger.error("Ошибка в loot_scheduler: %s", e)
