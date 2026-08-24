from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.models_subscription import PLAN_NAMES, PLAN_PRICES_USDT, PLAN_PRICES_STARS


def sub_plans_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=f"👥 {PLAN_NAMES['duo']} — {PLAN_PRICES_STARS['duo']} ⭐ / {PLAN_PRICES_USDT['duo']} USDT",
        callback_data="sub_plan_duo",
    ))
    builder.row(InlineKeyboardButton(
        text=f"👥 {PLAN_NAMES['four']} — {PLAN_PRICES_STARS['four']} ⭐ / {PLAN_PRICES_USDT['four']} USDT",
        callback_data="sub_plan_four",
    ))
    builder.row(InlineKeyboardButton(
        text=f"♾ {PLAN_NAMES['unlimited']} — {PLAN_PRICES_STARS['unlimited']} ⭐ / {PLAN_PRICES_USDT['unlimited']} USDT",
        callback_data="sub_plan_unlimited",
    ))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="clan"))
    return builder.as_markup()


def sub_payment_kb(plan: str, order_id: int | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    stars = PLAN_PRICES_STARS[plan]
    builder.row(InlineKeyboardButton(
        text=f"⭐ Оплатить звёздами — {stars} Stars",
        callback_data=f"sub_stars_{plan}",
    ))
    builder.row(InlineKeyboardButton(
        text=f"💎 Оплатить TON (скидка 15%) — {PLAN_PRICES_USDT[plan]} USDT",
        callback_data=f"sub_ton_{plan}",
    ))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="clan_sub"))
    return builder.as_markup()


def sub_ton_check_kb(order_id: int, plan: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🔄 Проверить оплату",
        callback_data=f"sub_ton_check_{order_id}",
    ))
    builder.row(InlineKeyboardButton(
        text="❌ Отменить",
        callback_data=f"sub_plan_{plan}",
    ))
    return builder.as_markup()


def presub_plans_kb(show_trial: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if show_trial:
        builder.row(InlineKeyboardButton(
            text="🎁 Попробовать бесплатно — 2 дня",
            callback_data="presub_trial",
        ))
    builder.row(InlineKeyboardButton(
        text=f"👥 {PLAN_NAMES['duo']} — {PLAN_PRICES_STARS['duo']} ⭐ / {PLAN_PRICES_USDT['duo']} USDT",
        callback_data="presub_plan_duo",
    ))
    builder.row(InlineKeyboardButton(
        text=f"👥 {PLAN_NAMES['four']} — {PLAN_PRICES_STARS['four']} ⭐ / {PLAN_PRICES_USDT['four']} USDT",
        callback_data="presub_plan_four",
    ))
    builder.row(InlineKeyboardButton(
        text=f"♾ {PLAN_NAMES['unlimited']} — {PLAN_PRICES_STARS['unlimited']} ⭐ / {PLAN_PRICES_USDT['unlimited']} USDT",
        callback_data="presub_plan_unlimited",
    ))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="clan"))
    return builder.as_markup()


def presub_payment_kb(plan: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=f"⭐ Оплатить звёздами — {PLAN_PRICES_STARS[plan]} Stars",
        callback_data=f"presub_stars_{plan}",
    ))
    builder.row(InlineKeyboardButton(
        text=f"💎 Оплатить TON (скидка 15%) — {PLAN_PRICES_USDT[plan]} USDT",
        callback_data=f"presub_ton_{plan}",
    ))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="clan_create"))
    return builder.as_markup()


def presub_ton_check_kb(order_id: int, plan: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🔄 Проверить оплату",
        callback_data=f"presub_ton_check_{order_id}",
    ))
    builder.row(InlineKeyboardButton(
        text="❌ Отменить",
        callback_data=f"presub_plan_{plan}",
    ))
    return builder.as_markup()


def presub_after_pay_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Создать клан", callback_data="clan_create"))
    return builder.as_markup()


def sub_back_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ К подпискам", callback_data="clan_sub"))
    builder.row(InlineKeyboardButton(text="🏠 Клан", callback_data="clan"))
    return builder.as_markup()
