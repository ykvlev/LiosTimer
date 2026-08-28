from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def clan_menu_no_clan() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Создать клан", callback_data="clan_create"),
        InlineKeyboardButton(text="🔑 Вступить", callback_data="clan_join"),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def clan_menu_in_clan(
    role: str = "member",
    server_label: str | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    is_manager = role in ("owner", "moderator")
    srv_text = server_label if server_label else "Сервер клана — не выбран"
    builder.row(InlineKeyboardButton(
        text=srv_text,
        callback_data="clan_server",
        icon_custom_emoji_id="5258419835922030550",
    ))
    builder.row(InlineKeyboardButton(text="👥 Участники", callback_data="clan_members"))
    if is_manager:
        builder.row(InlineKeyboardButton(text="⚙️ Настройки клана", callback_data="clan_settings"))
    else:
        builder.row(InlineKeyboardButton(text="🚪 Покинуть клан", callback_data="clan_leave"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def clan_settings_kb(has_photo: bool, is_owner: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить название", callback_data="clan_rename"),
        InlineKeyboardButton(text="🏷 Изменить тег",      callback_data="clan_retag"),
    )
    if has_photo:
        builder.row(InlineKeyboardButton(text="🔄 Сменить фото клана", callback_data="clan_photo_set"))
        builder.row(InlineKeyboardButton(text="🗑 Удалить фото клана", callback_data="clan_photo_del"))
    else:
        builder.row(InlineKeyboardButton(text="🖼 Установить фото клана", callback_data="clan_photo_set"))
    if is_owner:
        builder.row(InlineKeyboardButton(text="🗑 Распустить клан", callback_data="clan_disband_confirm"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="clan"))
    return builder.as_markup()


def clan_disband_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, распустить", callback_data="clan_disband"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="clan_settings"),
    )
    return builder.as_markup()


def clan_photo_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="clan_settings"))
    return builder.as_markup()


def clan_server_kb(is_manager: bool, has_server: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_manager:
        builder.row(InlineKeyboardButton(
            text="📋 Выбрать из моих" if not has_server else "🔄 Сменить сервер",
            callback_data="clan_server_pick",
        ))
        builder.row(InlineKeyboardButton(
            text="➕ Создать новый",
            callback_data="clan_server_new",
        ))
        if has_server:
            builder.row(InlineKeyboardButton(
                text="❌ Убрать сервер",
                callback_data="clan_server_remove",
            ))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="clan"))
    return builder.as_markup()


def clan_server_pick_kb(servers: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in servers:
        builder.row(InlineKeyboardButton(
            text=f"🧹 {s['name']}",
            callback_data=f"clan_server_use_{s['id']}",
        ))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="clan_server"))
    return builder.as_markup()


def clan_members_kb(members: list[dict], viewer_role: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    is_manager = viewer_role in ("owner", "moderator")
    for m in members:
        name = m["first_name"] or m["username"] or f"id{m['user_id']}"
        if m["role"] == "owner":
            role_icon = "👑"
        elif m["role"] == "moderator":
            role_icon = "🛡"
        else:
            role_icon = "🧑"
        can_manage = (
            is_manager
            and m["role"] != "owner"
            and not (viewer_role == "moderator" and m["role"] == "moderator")
        )
        if can_manage:
            builder.row(InlineKeyboardButton(
                text=f"{role_icon} {name}",
                callback_data=f"clan_member_{m['user_id']}",
            ))
        else:
            builder.row(InlineKeyboardButton(
                text=f"{role_icon} {name}",
                callback_data="noop",
            ))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="clan"))
    return builder.as_markup()


def clan_member_profile_kb(user_id: int, target_role: str, viewer_role: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if viewer_role == "owner":
        if target_role == "member":
            builder.row(InlineKeyboardButton(
                text="🛡 Назначить модератором",
                callback_data=f"clan_setmod_{user_id}",
            ))
        elif target_role == "moderator":
            builder.row(InlineKeyboardButton(
                text="🧑 Снять модератора",
                callback_data=f"clan_unsetmod_{user_id}",
            ))
    can_kick = (
        viewer_role == "owner"
        or (viewer_role == "moderator" and target_role == "member")
    )
    if can_kick:
        builder.row(InlineKeyboardButton(text="🚫 Выгнать", callback_data=f"clan_kick_{user_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="clan_members"))
    return builder.as_markup()


def clan_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="clan"))
    return builder.as_markup()


def clan_server_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="clan_server"))
    return builder.as_markup()
