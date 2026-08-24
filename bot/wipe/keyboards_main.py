from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.models_wipe import format_countdown


def wipe_main_kb(active_server: dict | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if active_server:
        countdown = format_countdown(active_server["hours_left"])
        label = f"✅ {active_server['name']} — {countdown}"
        builder.row(
            InlineKeyboardButton(text=label, callback_data=f"wipe_server_{active_server['id']}"),
        )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить сервер", callback_data="wipe_add"),
        InlineKeyboardButton(text="📋 Мои серверы", callback_data="wipe_servers"),
    )
    builder.row(
        InlineKeyboardButton(text="🚀 Старт нового вайпа", callback_data="wipe_quickstart"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"),
    )
    return builder.as_markup()


def wipe_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="wipe"))
    return builder.as_markup()
