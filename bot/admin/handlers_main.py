from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config.settings import load_config
from data.models_users import get_total_users, get_users_today, get_users_week, get_user_is_admin
from data.models_settings import get_global_photo, set_global_photo, delete_global_photo
from data.models_loot import get_active_cd_stats, LOCATIONS, LOOT_ITEM_LABELS
from data.models_miniboss import MINIBOSS_ROOMS
from bot.admin.keyboards_main import admin_main_kb
from bot.utils.nav import safe_edit_text
from states.states_admin import AdminMenuPhoto

router = Router()
config = load_config()


def is_superadmin(user_id: int) -> bool:
    return user_id == config.admin_id


async def is_admin(user_id: int) -> bool:
    return user_id == config.admin_id or await get_user_is_admin(user_id)


async def admin_text() -> str:
    total = await get_total_users()
    today = await get_users_today()
    week = await get_users_week()
    return (
        "🔧 <b>Админ-панель</b>\n"
        "\n"
        "📊 <b>Статистика:</b>\n"
        f"👤 Всего пользователей: <b>{total}</b>\n"
        f"📅 Сегодня: <b>{today}</b>\n"
        f"📆 За неделю: <b>{week}</b>"
    )


def _admin_photo_kb(has_photo: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="📤 Загрузить фото" if not has_photo else "🔄 Заменить фото",
        callback_data="admin_menu_photo_set",
    ))
    if has_photo:
        builder.row(InlineKeyboardButton(text="🗑 Удалить фото", callback_data="admin_menu_photo_del"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel"))
    return builder.as_markup()


def _admin_photo_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu_photo"))
    return builder.as_markup()


@router.callback_query(F.data == "admin_menu_photo")
async def admin_menu_photo_handler(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.clear()
    photo = await get_global_photo()
    text = "🖼 <b>Фото главного меню</b>\n\n" + (
        "Текущее фото установлено." if photo else "Фото не установлено."
    )
    await safe_edit_text(callback.message, text, parse_mode="HTML", reply_markup=_admin_photo_kb(bool(photo)))
    await callback.answer()


@router.callback_query(F.data == "admin_menu_photo_set")
async def admin_menu_photo_set(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.set_state(AdminMenuPhoto.waiting_photo)
    await safe_edit_text(
        callback.message,
        "🖼 Отправь фото, которое будет доступно всем пользователям как фото главного меню.",
        reply_markup=_admin_photo_cancel_kb(),
    )
    await callback.answer()


@router.message(AdminMenuPhoto.waiting_photo, F.photo)
async def admin_menu_photo_receive(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    file_id = message.photo[-1].file_id
    await set_global_photo(file_id)
    await state.clear()
    await message.answer(
        "✅ Фото сохранено! Пользователи смогут установить его через настройки.",
        reply_markup=_admin_photo_kb(has_photo=True),
    )


@router.message(AdminMenuPhoto.waiting_photo)
async def admin_menu_photo_wrong(message: Message):
    if not await is_admin(message.from_user.id):
        return
    await message.answer("❗ Нужно отправить фото.", reply_markup=_admin_photo_cancel_kb())


@router.callback_query(F.data == "admin_menu_photo_del")
async def admin_menu_photo_delete(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await delete_global_photo()
    await safe_edit_text(
        callback.message,
        "🖼 <b>Фото главного меню</b>\n\nФото не установлено.",
        parse_mode="HTML",
        reply_markup=_admin_photo_kb(has_photo=False),
    )
    await callback.answer("🗑 Фото удалено")


def _loc_label(loc: str) -> tuple[str, str]:
    if loc in LOCATIONS:
        return LOCATIONS[loc]["emoji"], LOCATIONS[loc]["name"]
    if loc in LOOT_ITEM_LABELS:
        return LOOT_ITEM_LABELS[loc]
    if loc in MINIBOSS_ROOMS:
        return MINIBOSS_ROOMS[loc]["emoji"], MINIBOSS_ROOMS[loc]["name"]
    return "▪️", loc


def _format_by_loc(by_loc: dict[str, int]) -> list[str]:
    lines = []
    for loc, cnt in by_loc.items():
        emoji, name = _loc_label(loc)
        lines.append(f"   {emoji} {name}: <b>{cnt}</b>")
    return lines


@router.callback_query(F.data == "admin_cd_stats")
async def admin_cd_stats_handler(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    s = await get_active_cd_stats()
    p, c, m = s["personal"], s["clan"], s["miniboss"]

    lines = [
        "📈 <b>Статистика активных КД</b>\n",
        f"👤 Уникальных игроков: <b>{s['unique_users']}</b>",
        f"⏱ Всего таймеров: <b>{s['total_slots']}</b>",
        "",
        "📦 <b>По разделам:</b>",
        f"🏠 Личные комнаты: <b>{p['slots']}</b> "
        f"({p['users']} {'игрок' if p['users'] == 1 else 'игроков'})",
        f"👥 Клановые комнаты: <b>{c['slots']}</b> "
        f"({c['clans']} {'клан' if c['clans'] == 1 else 'кланов'})",
        f"👹 Минибоссы: <b>{m['slots']}</b> "
        f"({m['users']} {'игрок' if m['users'] == 1 else 'игроков'})",
    ]

    if p["by_loc"]:
        lines.append("\n🏠 <b>Личные локации:</b>")
        lines.extend(_format_by_loc(p["by_loc"]))
    if c["by_loc"]:
        lines.append("\n👥 <b>Клановые локации:</b>")
        lines.extend(_format_by_loc(c["by_loc"]))
    if m["by_loc"]:
        lines.append("\n👹 <b>Минибоссы:</b>")
        lines.extend(_format_by_loc(m["by_loc"]))

    if s["total_slots"] == 0:
        lines.append("\n<i>Сейчас нет активных таймеров.</i>")

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_cd_stats"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel"))
    await safe_edit_text(
        callback.message,
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin")
@router.callback_query(F.data == "admin_panel")
async def admin_handler(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.clear()
    text = await admin_text()
    await safe_edit_text(callback.message, text, parse_mode="HTML", reply_markup=admin_main_kb())
    await callback.answer()
