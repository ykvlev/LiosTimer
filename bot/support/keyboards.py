from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def support_intro_kb(has_open_ticket: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="✍️ Продолжить диалог" if has_open_ticket else "✍️ Написать разработчикам",
        callback_data="support_write",
    ))
    if has_open_ticket:
        builder.row(InlineKeyboardButton(text="✅ Завершить диалог", callback_data="support_close"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def support_chat_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Завершить диалог", callback_data="support_close"))
    builder.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu"))
    return builder.as_markup()


def admin_ticket_notify_kb(ticket_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💬 Ответить", callback_data=f"sup_reply_{ticket_id}"))
    builder.row(InlineKeyboardButton(text="✅ Закрыть обращение", callback_data=f"sup_close_{ticket_id}"))
    return builder.as_markup()


def admin_tickets_kb(tickets: list[dict], page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in tickets:
        preview = (t.get("last_text") or "").replace("\n", " ")[:28]
        builder.row(InlineKeyboardButton(
            text=f"#{t['id']} • {preview or 'без сообщений'}",
            callback_data=f"sup_ticket_{t['id']}_{page}",
        ))
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_tickets_{page - 1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_tickets_{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel"))
    return builder.as_markup()


def admin_ticket_kb(ticket_id: int, page: int, is_open: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_open:
        builder.row(InlineKeyboardButton(text="💬 Ответить", callback_data=f"sup_reply_{ticket_id}"))
        builder.row(InlineKeyboardButton(text="✅ Закрыть обращение", callback_data=f"sup_close_{ticket_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_tickets_{page}"))
    return builder.as_markup()


def admin_reply_cancel_kb(ticket_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"sup_ticket_{ticket_id}_1"))
    return builder.as_markup()
