from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_users_kb(users: list[dict], page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for u in users:
        name = u["first_name"] or "—"
        username = f"@{u['username']}" if u["username"] else "нет юзернейма"
        if u.get("is_banned"):
            mark = "🚫 "
        elif u.get("is_admin"):
            mark = "👑 "
        else:
            mark = ""
        builder.row(
            InlineKeyboardButton(
                text=f"{mark}{name} | {username}",
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


def _staff_label(u: dict) -> str:
    if u.get("is_super_admin"):
        role = "⭐"
    elif u.get("is_admin"):
        role = "👑"
    else:
        role = "🛡"
    name = u["first_name"] or "—"
    username = f"@{u['username']}" if u["username"] else "нет юзернейма"
    return f"{role} {name} | {username}"


def admin_staff_kb(staff: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for u in staff:
        builder.row(
            InlineKeyboardButton(
                text=_staff_label(u),
                callback_data=f"admin_user_{u['user_id']}_0",
            )
        )
    builder.row(
        InlineKeyboardButton(text="👑 Выдать админа по @", callback_data="admin_byusername"),
    )
    builder.row(
        InlineKeyboardButton(text="🛡 Выдать модера по @", callback_data="admin_modbyusername"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel"),
    )
    return builder.as_markup()


def admin_user_profile_kb(
    user_id: int,
    is_admin: bool,
    page: int,
    is_moderator: bool = False,
    can_manage: bool = False,
    is_staff: bool = False,
    is_banned: bool = False,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_manage:
        if is_admin:
            builder.row(InlineKeyboardButton(
                text="❌ Забрать админа", callback_data=f"admin_revoke_{user_id}_{page}"))
        else:
            builder.row(InlineKeyboardButton(
                text="👑 Выдать админа", callback_data=f"admin_grant_{user_id}_{page}"))
        if is_moderator:
            builder.row(InlineKeyboardButton(
                text="❌ Забрать модера", callback_data=f"admin_unsetmod_{user_id}_{page}"))
        else:
            builder.row(InlineKeyboardButton(
                text="🛡 Выдать модера", callback_data=f"admin_setmod_{user_id}_{page}"))
    # Банить может любой админ, но не персонал.
    if not is_staff:
        if is_banned:
            builder.row(InlineKeyboardButton(
                text="✅ Разблокировать", callback_data=f"admin_unban_{user_id}_{page}"))
        else:
            builder.row(InlineKeyboardButton(
                text="🚫 Заблокировать", callback_data=f"admin_ban_{user_id}_{page}"))
    back = "admin_staff" if page == 0 else f"admin_users_{page}"
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=back))
    return builder.as_markup()


def admin_search_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel"))
    return builder.as_markup()
