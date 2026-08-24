from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.models_loot import LOCATIONS, CARD_NAMES, format_time_left, format_minutes


def loot_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Чипы", callback_data="rooms", icon_custom_emoji_id="5307762520457507728"),
        InlineKeyboardButton(text="Танк", callback_data="loot_tank", icon_custom_emoji_id="5325863428198265230"),
    )
    builder.row(
        InlineKeyboardButton(text="Мститель", callback_data="loot_avenger", icon_custom_emoji_id="5341780894824831113"),
        InlineKeyboardButton(text="Монст Егг", callback_data="loot_egg", icon_custom_emoji_id="5341313306030283326"),
    )
    builder.row(
        InlineKeyboardButton(text="Вертолет", callback_data="loot_heli",   icon_custom_emoji_id="5323546495205536651"),
        InlineKeyboardButton(text="Десант",   callback_data="loot_patrol", icon_custom_emoji_id="5386642223368530459"),
        InlineKeyboardButton(text="Карго",    callback_data="loot_cargo",  icon_custom_emoji_id="5323526957399308323"),
    )
    builder.row(
        InlineKeyboardButton(text="Мини-боссы", callback_data="loot_miniboss", icon_custom_emoji_id="5348271844539537866"),
    )
    builder.row(
        InlineKeyboardButton(text="Медаль", callback_data="loot_medal", icon_custom_emoji_id="5305349315772839031"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"),
    )
    return builder.as_markup()


def _location_status(loc_key: str, slots_data: dict) -> str:
    loc = LOCATIONS[loc_key]
    total = loc["slots"]
    configured = 0
    on_cd = 0
    for i in range(total):
        row = slots_data.get((loc_key, i))
        if not row or not row.get("card_type"):
            continue
        configured += 1
        if row.get("seconds_left", 0) > 0:
            on_cd += 1
    if configured == 0:
        if LOCATIONS[loc_key]["fixed"]:
            return ""
        return "⚪"
    if on_cd > 0:
        return "⏳"
    return ""


def rooms_list_kb(slots_data: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for loc_key, loc in LOCATIONS.items():
        status = _location_status(loc_key, slots_data)
        builder.add(
            InlineKeyboardButton(
                text=f"{loc['emoji']} {loc['name']}{' ' + status if status else ''}",
                callback_data=f"room_{loc_key}",
            )
        )
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="loot"),
    )
    return builder.as_markup()


def location_kb(loc_key: str, slots_data: dict, show_settings: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    loc = LOCATIONS[loc_key]
    for i in range(loc["slots"]):
        row = slots_data.get((loc_key, i))
        card_type = row["card_type"] if row else None
        seconds_left = row["seconds_left"] if row else 0.0

        if not card_type:
            builder.row(InlineKeyboardButton(
                text=f"Чип {i + 1}: ❓ не указан",
                callback_data=f"rslot_{loc_key}_{i}",
            ))
        elif card_type == "blue":
            if seconds_left > 0:
                label = f"Синий чип — ⏳ {format_time_left(seconds_left)}"
            else:
                label = "Синий чип"
            builder.row(InlineKeyboardButton(
                text=label,
                callback_data=f"rslot_{loc_key}_{i}",
                icon_custom_emoji_id="5305359387471149323",
            ))
        else:
            chip_name = "Фиолетовый чип" if card_type == "purple" else f"{CARD_NAMES[card_type]} чип"
            if seconds_left > 0:
                label = f"{chip_name} — ⏳ {format_time_left(seconds_left)}"
            else:
                label = chip_name
            builder.row(InlineKeyboardButton(
                text=label,
                callback_data=f"rslot_{loc_key}_{i}",
                icon_custom_emoji_id="5307762520457507728",
            ))
    row = []
    if show_settings:
        row.append(InlineKeyboardButton(text="⚙️ Настройка", callback_data=f"rconf_{loc_key}"))
    row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="rooms"))
    builder.row(*row)
    return builder.as_markup()


def slot_kb(loc_key: str, slot: int, card_type: str | None, seconds_left: float, is_fixed: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not card_type:
        builder.row(
            InlineKeyboardButton(text="Синяя",      callback_data=f"rset_{loc_key}_{slot}_blue",   icon_custom_emoji_id="5305359387471149323"),
            InlineKeyboardButton(text="Фиолетовая", callback_data=f"rset_{loc_key}_{slot}_purple", icon_custom_emoji_id="5307762520457507728"),
        )
    elif seconds_left > 0:
        builder.row(
            InlineKeyboardButton(text="🔄 Сбросить", callback_data=f"rreset_{loc_key}_{slot}"),
        )
    else:
        builder.row(
            InlineKeyboardButton(text="✅ Залутал", callback_data=f"rloot_{loc_key}_{slot}"),
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"room_{loc_key}"),
    )
    return builder.as_markup()


def location_settings_main_kb(loc_key: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Сменить карты",        callback_data=f"rchangecards_{loc_key}"),
    )
    builder.row(
        InlineKeyboardButton(text="⏱ Настроить спавн карт", callback_data=f"rspawn_{loc_key}"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"room_{loc_key}"),
    )
    return builder.as_markup()


def location_spawn_kb(loc_key: str, cd_minutes: dict[str, int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f'Синяя: {format_minutes(cd_minutes["blue"])} ✏️',
            callback_data=f"rcdset_{loc_key}_blue",
            icon_custom_emoji_id="5305359387471149323",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"Фиолетовая: {format_minutes(cd_minutes['purple'])} ✏️",
            callback_data=f"rcdset_{loc_key}_purple",
            icon_custom_emoji_id="5307762520457507728",
        )
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rconf_{loc_key}"),
    )
    return builder.as_markup()


def location_cards_edit_kb(loc_key: str, slots_data: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    loc = LOCATIONS[loc_key]
    for i in range(loc["slots"]):
        row = slots_data.get((loc_key, i))
        card_type = row["card_type"] if row else None
        if not card_type:
            builder.row(InlineKeyboardButton(
                text=f"Чип {i + 1}: ❓ не указан",
                callback_data=f"redit_{loc_key}_{i}",
            ))
        elif card_type == "blue":
            builder.row(InlineKeyboardButton(
                text="Синий чип ✏️",
                callback_data=f"redit_{loc_key}_{i}",
                icon_custom_emoji_id="5305359387471149323",
            ))
        else:
            chip_name = "Фиолетовый чип" if card_type == "purple" else f"{CARD_NAMES[card_type]} чип"
            builder.row(InlineKeyboardButton(
                text=f"{chip_name} ✏️",
                callback_data=f"redit_{loc_key}_{i}",
                icon_custom_emoji_id="5307762520457507728",
            ))
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rconf_{loc_key}"),
    )
    return builder.as_markup()


def slot_edit_kb(loc_key: str, slot: int, current_card: str | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    blue_mark   = "✅ " if current_card == "blue"   else ""
    purple_mark = "✅ " if current_card == "purple" else ""
    builder.row(
        InlineKeyboardButton(text=f"{blue_mark}Синяя",      callback_data=f"rsave_{loc_key}_{slot}_blue",   icon_custom_emoji_id="5305359387471149323"),
        InlineKeyboardButton(text=f"{purple_mark}Фиолетовая", callback_data=f"rsave_{loc_key}_{slot}_purple", icon_custom_emoji_id="5307762520457507728"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rchangecards_{loc_key}"),
    )
    return builder.as_markup()


def event_settings_kb(event: str, back_cb: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить кулдаун", callback_data=f"evcdset_{event}"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb),
    )
    return builder.as_markup()


def event_cd_cancel_kb(event: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"evset_{event}"),
    )
    return builder.as_markup()


def loot_notify_choice_kb(confirm_prefix: str, back_cb: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔔 Напомнить", callback_data=f"{confirm_prefix}_once"),
        InlineKeyboardButton(text="🔕 Без напоминания", callback_data=f"{confirm_prefix}_none"),
    )
    builder.row(
        InlineKeyboardButton(text="🔁 Авто x2", callback_data=f"{confirm_prefix}_twice"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb),
    )
    return builder.as_markup()


def notify_loot_quick_kb(loc_key: str, slot: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Залутал", callback_data=f"nloot_{loc_key}_{slot}"),
    )
    return builder.as_markup()


def cd_cancel_kb(loc_key: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"rspawn_{loc_key}"),
    )
    return builder.as_markup()
