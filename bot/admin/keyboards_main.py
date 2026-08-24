from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users_1"),
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
