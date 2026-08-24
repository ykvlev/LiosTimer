from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def notifications_kb(settings: dict) -> InlineKeyboardMarkup:
    def btn(key: str, label: str) -> InlineKeyboardButton:
        icon = "✅" if settings.get(key) else "❌"
        return InlineKeyboardButton(
            text=f"{icon} {label}",
            callback_data=f"notif_toggle:{key}",
        )

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            btn("loot",       "Лут готов"),
            btn("wipe_start", "Вайп начался"),
        ],
        [
            btn("wipe_1h", "Вайп через 1ч"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"),
        ],
    ])
