from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_users_kb(users: list[dict], page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for u in users:
        name = u["first_name"] or "—"
        username = f"@{u['username']}" if u["username"] else "нет юзернейма"
        crown = "👑 " if u.get("is_admin") else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{crown}{name} | {username}",
                callback_data=f"admin_user_{u['user_id']}_{page}",
            )
        )

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"admin_users_{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"admin_users_{page + 1}"))
    builder.row(*nav)

    builder.row(
        InlineKeyboardButton(text="🔍 Поиск", callback_data="admin_search"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel"),
    )
    builder.row(
        InlineKeyboardButton(text="👑 Выдать по @", callback_data="admin_byusername"),
    )
    return builder.as_markup()


def admin_user_profile_kb(user_id: int, is_admin: bool, page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="❌ Забрать права", callback_data=f"admin_revoke_{user_id}_{page}"),
        )
    else:
        builder.row(
            InlineKeyboardButton(text="👑 Выдать права", callback_data=f"admin_grant_{user_id}_{page}"),
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_users_{page}"),
    )
    return builder.as_markup()


def admin_search_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel"))
    return builder.as_markup()
