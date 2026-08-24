from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.models_miniboss import MINIBOSS_ROOMS, format_time_left


def miniboss_kb(rooms_data: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for loc_key, loc in MINIBOSS_ROOMS.items():
        row = rooms_data.get(loc_key)
        seconds_left = row["seconds_left"] if row else 0.0

        if seconds_left > 0:
            info_text = f"⏳ {loc['emoji']} {loc['name']} — {format_time_left(seconds_left)}"
            action_btn = InlineKeyboardButton(text="🔄 Сброс", callback_data=f"mb_reset_{loc_key}")
        else:
            info_text = f"{loc['emoji']} {loc['name']}"
            action_btn = InlineKeyboardButton(text="☑️ Слутал", callback_data=f"mb_loot_{loc_key}")

        builder.row(
            InlineKeyboardButton(text=info_text, callback_data="loot_miniboss"),
            action_btn,
        )

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="loot"))
    return builder.as_markup()
