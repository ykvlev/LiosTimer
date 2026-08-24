from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def patrol_kb(seconds_left: float, show_settings: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if seconds_left > 0:
        builder.row(InlineKeyboardButton(text="🔄 Сбросить", callback_data="patrol_reset"))
    else:
        builder.row(InlineKeyboardButton(text="✅ Залутал", callback_data="patrol_loot"))
    row = []
    if show_settings:
        row.append(InlineKeyboardButton(text="⚙️ Настройка", callback_data="evset_patrol"))
    row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="loot"))
    builder.row(*row)
    return builder.as_markup()
