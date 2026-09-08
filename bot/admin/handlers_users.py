from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from config.settings import load_config
from data.models_users import (
    get_users_page, get_pages_count, search_users, get_user_by_id, set_admin,
    get_user_is_admin, get_user_is_super_admin, get_user_by_username,
    get_staff, set_moderator,
)
from bot.admin.keyboards_main import admin_main_kb
from bot.admin.keyboards_users import (
    admin_users_kb, admin_user_profile_kb, admin_search_cancel_kb, admin_staff_kb,
)
from states.states_admin import AdminSearch, AdminGrantByUsername, AdminGrantModByUsername

router = Router()
config = load_config()


async def is_superadmin(user_id: int) -> bool:
    return user_id == config.admin_id or await get_user_is_super_admin(user_id)


async def is_admin(user_id: int) -> bool:
    return user_id == config.admin_id or await get_user_is_admin(user_id)


def _role_of(u: dict) -> str:
    if u.get("is_super_admin"):
        return "⭐ Супер-админ"
    if u.get("is_admin"):
        return "👑 Администратор"
    if u.get("is_moderator"):
        return "🛡 Модератор"
    return "👤 Пользователь"


def _profile_text(u: dict) -> str:
    name = u["first_name"] or "—"
    username = f"@{u['username']}" if u["username"] else "нет юзернейма"
    return (
        f"👤 <b>{name}</b>\n"
        f"🔗 {username}\n"
        f"🆔 <code>{u['user_id']}</code>\n"
        f"📅 Зарегистрирован: {u['created_at'][:10] if u['created_at'] else '—'}\n"
        f"\nРоль: {_role_of(u)}"
    )


async def _render_profile(callback: CallbackQuery, user_id: int, page: int):
    u = await get_user_by_id(user_id)
    if not u:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    can_manage = await is_superadmin(callback.from_user.id)
    await callback.message.edit_text(
        _profile_text(u), parse_mode="HTML",
        reply_markup=admin_user_profile_kb(
            user_id, bool(u["is_admin"]), page,
            is_moderator=bool(u.get("is_moderator")), can_manage=can_manage,
        ),
    )


@router.callback_query(F.data.startswith("admin_users_"))
async def admin_users(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    page = int(callback.data.split("_")[-1])
    total_pages = await get_pages_count()
    users = await get_users_page(page)
    text = f"👥 <b>Пользователи</b> (стр. {page}/{total_pages})"
    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=admin_users_kb(users, page, total_pages),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_staff")
async def admin_staff(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    staff = await get_staff()
    text = (
        "🛡 <b>Персонал</b>\n\n"
        "⭐ супер-админ · 👑 админ · 🛡 модератор\n\n"
        + ("Пока только ты." if not staff else "Нажми на человека, чтобы изменить роль.")
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_staff_kb(staff))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_user_"))
async def admin_user_profile(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    try:
        parts = callback.data.split("_")
        page = int(parts[-1])
        user_id = int(parts[-2])
    except (IndexError, ValueError):
        await callback.answer("Ошибка данных", show_alert=True)
        return
    await _render_profile(callback, user_id, page)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_grant_"))
async def admin_grant(callback: CallbackQuery):
    if not await is_superadmin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    parts = callback.data.split("_")
    user_id, page = int(parts[2]), int(parts[3])
    await set_admin(user_id, True)
    u = await get_user_by_id(user_id)
    await callback.answer(f"✅ {u['first_name'] or user_id} теперь администратор", show_alert=True)
    await _render_profile(callback, user_id, page)


@router.callback_query(F.data.startswith("admin_revoke_"))
async def admin_revoke(callback: CallbackQuery):
    if not await is_superadmin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    parts = callback.data.split("_")
    user_id, page = int(parts[2]), int(parts[3])
    await set_admin(user_id, False)
    u = await get_user_by_id(user_id)
    await callback.answer(f"❌ У {u['first_name'] or user_id} забраны права админа", show_alert=True)
    await _render_profile(callback, user_id, page)


@router.callback_query(F.data.startswith("admin_setmod_"))
async def admin_setmod(callback: CallbackQuery):
    if not await is_superadmin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    parts = callback.data.split("_")
    user_id, page = int(parts[2]), int(parts[3])
    await set_moderator(user_id, True)
    u = await get_user_by_id(user_id)
    await callback.answer(f"🛡 {u['first_name'] or user_id} теперь модератор", show_alert=True)
    await _render_profile(callback, user_id, page)


@router.callback_query(F.data.startswith("admin_unsetmod_"))
async def admin_unsetmod(callback: CallbackQuery):
    if not await is_superadmin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    parts = callback.data.split("_")
    user_id, page = int(parts[2]), int(parts[3])
    await set_moderator(user_id, False)
    u = await get_user_by_id(user_id)
    await callback.answer(f"❌ У {u['first_name'] or user_id} забраны права модератора", show_alert=True)
    await _render_profile(callback, user_id, page)


@router.callback_query(F.data == "admin_search")
async def admin_search_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.set_state(AdminSearch.waiting_query)
    await callback.message.edit_text(
        "🔍 Введи имя, юзернейм или ID пользователя:",
        reply_markup=admin_search_cancel_kb(),
    )
    await callback.answer()


@router.message(AdminSearch.waiting_query)
async def admin_search_result(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    await state.clear()
    query = message.text.strip()
    users = await search_users(query)
    if not users:
        await message.answer(
            f"🔍 По запросу <b>{query}</b> ничего не найдено.",
            parse_mode="HTML",
            reply_markup=admin_main_kb(),
        )
        return
    total_pages = max(1, -(-len(users) // 10))
    await message.answer(
        f"🔍 <b>Результат:</b> {query} — найдено {len(users)}",
        parse_mode="HTML",
        reply_markup=admin_users_kb(users[:10], 1, total_pages),
    )


@router.callback_query(F.data == "admin_byusername")
async def admin_grant_by_username_start(callback: CallbackQuery, state: FSMContext):
    if not await is_superadmin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.set_state(AdminGrantByUsername.waiting_username)
    await callback.message.edit_text(
        "👑 Введи @юзернейм пользователя, которому выдать права <b>администратора</b>:",
        parse_mode="HTML",
        reply_markup=admin_search_cancel_kb(),
    )
    await callback.answer()


@router.message(AdminGrantByUsername.waiting_username)
async def admin_grant_by_username_receive(message: Message, state: FSMContext):
    if not await is_superadmin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ Доступ запрещён", reply_markup=admin_main_kb())
        return
    await state.clear()
    username = message.text.strip().lstrip("@")
    u = await get_user_by_username(username)
    if not u:
        await message.answer(
            f"❌ Пользователь @{username} не найден в базе.\nОн должен сначала запустить бота.",
            reply_markup=admin_main_kb(),
        )
        return
    if u["is_admin"]:
        await message.answer(f"ℹ️ @{username} уже администратор.", reply_markup=admin_main_kb())
        return
    await set_admin(u["user_id"], True)
    name = u["first_name"] or f"@{username}"
    await message.answer(
        f"✅ <b>{name}</b> (@{username}) теперь администратор.",
        parse_mode="HTML", reply_markup=admin_main_kb(),
    )


@router.callback_query(F.data == "admin_modbyusername")
async def admin_grant_mod_by_username_start(callback: CallbackQuery, state: FSMContext):
    if not await is_superadmin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.set_state(AdminGrantModByUsername.waiting_username)
    await callback.message.edit_text(
        "🛡 Введи @юзернейм пользователя, которому выдать права <b>модератора</b>:",
        parse_mode="HTML",
        reply_markup=admin_search_cancel_kb(),
    )
    await callback.answer()


@router.message(AdminGrantModByUsername.waiting_username)
async def admin_grant_mod_by_username_receive(message: Message, state: FSMContext):
    if not await is_superadmin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ Доступ запрещён", reply_markup=admin_main_kb())
        return
    await state.clear()
    username = message.text.strip().lstrip("@")
    u = await get_user_by_username(username)
    if not u:
        await message.answer(
            f"❌ Пользователь @{username} не найден в базе.\nОн должен сначала запустить бота.",
            reply_markup=admin_main_kb(),
        )
        return
    if u.get("is_moderator"):
        await message.answer(f"ℹ️ @{username} уже модератор.", reply_markup=admin_main_kb())
        return
    await set_moderator(u["user_id"], True)
    name = u["first_name"] or f"@{username}"
    await message.answer(
        f"🛡 <b>{name}</b> (@{username}) теперь модератор.",
        parse_mode="HTML", reply_markup=admin_main_kb(),
    )


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()
