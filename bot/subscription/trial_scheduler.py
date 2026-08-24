import asyncio
import logging

from data.models_subscription import (
    get_trial_subs_for_reminder,
    increment_trial_remind_count,
    PLAN_NAMES,
)

logger = logging.getLogger(__name__)


async def trial_reminder_scheduler(bot):
    while True:
        await asyncio.sleep(3600)
        try:
            subs = await get_trial_subs_for_reminder()
            for sub in subs:
                remind_count = sub["trial_remind_count"]
                clan_name = sub["name"]
                owner_id = sub["owner_id"]
                expires = sub["expires_at"][:10]

                if remind_count == 0:
                    text = (
                        f"⚠️ <b>Пробная подписка клана «{clan_name}» истекает завтра!</b>\n\n"
                        f"Дата окончания: <b>{expires}</b>\n\n"
                        "Оформи подписку чтобы продолжить пользоваться кланом и приглашать участников.\n\n"
                        "<blockquote>Оформляя подписку, вы поддерживаете проект — помогаете ему жить, развиваться и становиться всё более полезным! 💙</blockquote>"
                    )
                else:
                    text = (
                        f"🔔 <b>Пробная подписка клана «{clan_name}» истекает сегодня!</b>\n\n"
                        f"Дата окончания: <b>{expires}</b>\n\n"
                        "Успей оформить подписку — иначе участники не смогут вступать в клан.\n\n"
                        "<blockquote>Оформляя подписку, вы поддерживаете проект — помогаете ему жить, развиваться и становиться всё более полезным! 💙</blockquote>"
                    )

                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                from aiogram.utils.keyboard import InlineKeyboardBuilder
                builder = InlineKeyboardBuilder()
                builder.row(InlineKeyboardButton(text="💎 Оформить подписку", callback_data="clan_sub"))
                kb = builder.as_markup()

                try:
                    await bot.send_message(owner_id, text, parse_mode="HTML", reply_markup=kb)
                    await increment_trial_remind_count(sub["clan_id"])
                except Exception as e:
                    logger.warning("trial reminder send error: %s", e)
        except Exception as e:
            logger.error("trial_reminder_scheduler error: %s", e)
