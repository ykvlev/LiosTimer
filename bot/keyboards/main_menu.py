from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from data.models_wipe import format_countdown


def main_menu(
    is_admin: bool = False,
    active_server: dict | None = None,
    clan_name: str | None = None,
    clan_server_label: str | None = None,
    is_moderator: bool = False,
) -> InlineKeyboardMarkup:
    clan_label = clan_name if clan_name else "Вступить в клан"

    if clan_server_label:
        wipe_row = InlineKeyboardButton(
            text=clan_server_label,
            callback_data="clan_wipe",
            icon_custom_emoji_id="5258419835922030550",
        )
    else:
        if active_server:
            countdown = format_countdown(active_server["hours_left"])
            wipe_label = f"Вайп {active_server['name']} — {countdown}"
        else:
            wipe_label = "Вайп"
        wipe_row = InlineKeyboardButton(
            text=wipe_label,
            callback_data="wipe",
            icon_custom_emoji_id="5258419835922030550",
        )

    rows = [
        [
            InlineKeyboardButton(text="🎮 Лутанье", callback_data="loot"),
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="notifications"),
        ],
        [wipe_row],
        [
            InlineKeyboardButton(text="🏆 Призовые сервера", callback_data="prize_servers"),
        ],
        [
            InlineKeyboardButton(text=clan_label, callback_data="clan", icon_custom_emoji_id="5453957997418004470"),
        ],
        [
            InlineKeyboardButton(text="🛠 Связь с разработчиками", callback_data="support"),
        ],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="🔧 Админ", callback_data="admin")])
    elif is_moderator:
        rows.append([InlineKeyboardButton(text="🛡 Модерка", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
