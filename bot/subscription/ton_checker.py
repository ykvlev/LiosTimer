import asyncio
import logging

import httpx

from config.settings import load_config
from data.models_subscription import (
    get_all_pending_ton_orders,
    mark_ton_order_paid,
    expire_old_ton_orders,
    PLAN_NAMES,
)

logger = logging.getLogger(__name__)

USDT_DECIMALS = 1_000_000


def _get_ton_wallet() -> str:
    return load_config().ton_wallet


async def check_ton_payment(memo: str, expected_usdt: float) -> tuple[bool, str | None]:
    wallet = _get_ton_wallet()
    url = f"https://tonapi.io/v2/accounts/{wallet}/events?limit=100"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers={"Accept": "application/json"})
        if resp.status_code != 200:
            return False, None
        data = resp.json()
        for event in data.get("events", []):
            for action in event.get("actions", []):
                if action.get("type") != "JettonTransfer":
                    continue
                jt = action.get("JettonTransfer", {})
                comment = jt.get("comment", "")
                if comment != memo:
                    continue
                try:
                    amount_raw = int(jt.get("amount", 0))
                except (ValueError, TypeError):
                    continue
                if amount_raw >= int(expected_usdt * USDT_DECIMALS):
                    return True, event.get("event_id")
    except Exception as e:
        logger.warning("TON check error: %s", e)
    return False, None


async def ton_payment_scheduler(bot=None):
    while True:
        await asyncio.sleep(60)
        try:
            await expire_old_ton_orders()
            orders = await get_all_pending_ton_orders()
            for order in orders:
                found, tx_hash = await check_ton_payment(order["memo"], order["amount_usdt"])
                if not found:
                    continue
                result = await mark_ton_order_paid(order["id"], tx_hash or "")
                if not result or not bot:
                    continue
                if result["type"] == "activate":
                    text = (
                        f"✅ <b>Оплата получена!</b>\n\n"
                        f"План: <b>{PLAN_NAMES[result['plan']]}</b>\n"
                        "Подписка клана активирована на 30 дней! 🎉"
                    )
                else:
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    from aiogram.utils.keyboard import InlineKeyboardBuilder
                    builder = InlineKeyboardBuilder()
                    builder.row(InlineKeyboardButton(text="➕ Создать клан", callback_data="clan_create"))
                    kb = builder.as_markup()
                    text = (
                        f"✅ <b>Оплата получена!</b>\n\n"
                        f"План: <b>{PLAN_NAMES[result['plan']]}</b>\n"
                        "Теперь создай клан — подписка применится автоматически 👇"
                    )
                try:
                    await bot.send_message(
                        result["user_id"],
                        text,
                        parse_mode="HTML",
                        reply_markup=kb if result["type"] == "credit" else None,
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.error("ton_payment_scheduler error: %s", e)
