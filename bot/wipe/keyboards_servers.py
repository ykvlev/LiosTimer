from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.models_wipe import format_countdown


def servers_list_kb(servers: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in servers:
        active_mark = "✅ " if s.get("is_active") else ""
        countdown = format_countdown(s["hours_left"])
        label = f"{active_mark}🧹 {s['name']} — {countdown}"
        builder.row(
            InlineKeyboardButton(text=label, callback_data=f"wipe_server_{s['id']}"),
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="wipe"),
    )
    return builder.as_markup()


def server_profile_kb(server_id: int, is_active: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_active:
        builder.row(
            InlineKeyboardButton(text="⭐ Сделать активным", callback_data=f"wipe_setactive_{server_id}"),
        )
    else:
        builder.row(
            InlineKeyboardButton(text="✅ Активный сервер", callback_data="noop"),
        )
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить", callback_data=f"wipe_edit_{server_id}"),
        InlineKeyboardButton(text="❌ Удалить", callback_data=f"wipe_delete_{server_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="wipe_servers"),
    )
    return builder.as_markup()


def wipe_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🆕 Новый вайп", callback_data="wipe_type_new"),
        InlineKeyboardButton(text="⏳ Старый вайп", callback_data="wipe_type_old"),
    )
    builder.row(
        InlineKeyboardButton(text="🔜 Вайп ещё не начался", callback_data="wipe_type_pending"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="wipe"),
    )
    return builder.as_markup()


def edit_cancel_kb(server_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"wipe_server_{server_id}"))
    return builder.as_markup()
