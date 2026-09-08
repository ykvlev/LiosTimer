from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_main_kb(open_tickets: int = 0, full: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if not full:
        # Модератор: только призовые сервера.
        builder.row(
            InlineKeyboardButton(text="🏆 Призовые сервера", callback_data="admin_prize"),
        )
        builder.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"),
        )
        return builder.as_markup()

    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users_1"),
        InlineKeyboardButton(text="🛡 Персонал", callback_data="admin_staff"),
    )
    tickets_label = "✉️ Обращения" + (f" ({open_tickets})" if open_tickets else "")
    builder.row(
        InlineKeyboardButton(text=tickets_label, callback_data="admin_tickets_1"),
    )
    builder.row(
        InlineKeyboardButton(text="🏆 Призовые сервера", callback_data="admin_prize"),
    )
    builder.row(
        InlineKeyboardButton(text="📈 Статистика КД", callback_data="admin_cd_stats"),
    )
    builder.row(
        InlineKeyboardButton(text="🖼 Фото меню", callback_data="admin_menu_photo"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"),
    )
    return builder.as_markup()
