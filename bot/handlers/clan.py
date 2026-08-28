from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.keyboards.clan_menu import (
    clan_menu_no_clan,
    clan_menu_in_clan,
    clan_members_kb,
    clan_member_profile_kb,
    clan_server_kb,
    clan_server_pick_kb,
    clan_cancel_kb,
    clan_server_cancel_kb,
    clan_settings_kb,
    clan_photo_cancel_kb,
    clan_disband_confirm_kb,
)
from bot.utils.nav import safe_edit_text
from data.models_clan import (
    get_user_clan,
    get_clan_by_tag,
    get_clan_by_name,
    create_clan,
    join_clan,
    leave_clan,
    kick_member,
    set_member_role,
    get_clan_members,
    get_clan_server_id,
    set_clan_server,
    remove_clan_server,
    get_clan_photo,
    set_clan_photo,
    delete_clan_photo,
    rename_clan,
    retag_clan,
)
from data.models_wipe import (
    get_servers,
    get_server,
    add_server,
    format_countdown,
    format_hours,
    parse_hours_input,
    WIPE_DURATION_HOURS,
)
from states.states_clan import ClanCreate, ClanJoin, ClanServerAdd, ClanSettings
from data.models_clan import MAX_CLAN_MEMBERS

router = Router()


async def _build_server_label(clan_id: int) -> str | None:
    server_id = await get_clan_server_id(clan_id)
    if not server_id:
        return None
    server = await get_server(server_id)
    if not server:
        return None
    countdown = format_countdown(server["hours_left"])
    return f"{server['name']} — {countdown}"


async def _clan_text(user_id: int) -> tuple[str, object]:
    clan = await get_user_clan(user_id)
    if not clan:
        text = (
            "👥 <b>Клан</b>\n\n"
            "Играй вместе с командой — все участники клана видят общие таймеры.\n\n"
            f"Создание клана бесплатное, до {MAX_CLAN_MEMBERS} участников."
        )
        return text, clan_menu_no_clan()
    role = clan["role"]
    members = await get_clan_members(clan["id"])
    server_label = await _build_server_label(clan["id"])
    role_labels = {"owner": "👑 Лидер", "moderator": "🛡 Модератор", "member": "🧑 Участник"}
    role_label = role_labels.get(role, "🧑 Участник")
    text = (
        f"👥 <b>{clan['name']}</b> <code>{clan['tag']}</code>\n\n"
        f"Участников: {len(members)}/{MAX_CLAN_MEMBERS}\n"
        f"Твоя роль: {role_label}\n\n"
        "Поделись тегом клана с друзьями — они смогут вступить."
    )
    return text, clan_menu_in_clan(role=role, server_label=server_label)


@router.callback_query(F.data == "clan")
async def clan_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text, kb = await _clan_text(callback.from_user.id)
    clan = await get_user_clan(callback.from_user.id)
    photo = await get_clan_photo(clan["id"]) if clan else None
    if photo:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        await safe_edit_text(callback.message, text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "clan_members")
async def clan_members_handler(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    if not clan:
        await callback.answer("Ты не в клане", show_alert=True)
        return
    viewer_role = clan["role"]
    is_manager = viewer_role in ("owner", "moderator")
    members = await get_clan_members(clan["id"])
    text = (
        f"👥 <b>Участники клана {clan['name']}</b>\n\n"
        f"Всего: {len(members)}\n"
        + ("Нажми на участника чтобы управлять." if is_manager else "")
    )
    await safe_edit_text(callback.message, text, reply_markup=clan_members_kb(members, viewer_role))
    await callback.answer()


@router.callback_query(F.data.startswith("clan_member_"))
async def clan_member_profile(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    viewer_role = clan["role"] if clan else None
    if not clan or viewer_role not in ("owner", "moderator"):
        await callback.answer("Нет прав", show_alert=True)
        return
    target_id = int(callback.data.split("_")[2])
    members = await get_clan_members(clan["id"])
    target = next((m for m in members if m["user_id"] == target_id), None)
    if not target:
        await callback.answer("Участник не найден", show_alert=True)
        return
    if target["role"] == "owner":
        await callback.answer("Нет прав", show_alert=True)
        return
    if viewer_role == "moderator" and target["role"] == "moderator":
        await callback.answer("Нет прав", show_alert=True)
        return
    name = target["first_name"] or target["username"] or f"id{target_id}"
    role_labels = {"moderator": "🛡 Модератор", "member": "🧑 Участник"}
    role_label = role_labels.get(target["role"], "🧑 Участник")
    text = (
        f"{role_label.split()[0]} <b>{name}</b>\n\n"
        f"Роль: {role_label}\n"
        f"Клан: {clan['name']}"
    )
    await safe_edit_text(callback.message, text, reply_markup=clan_member_profile_kb(target_id, target["role"], viewer_role))
    await callback.answer()


@router.callback_query(F.data.startswith("clan_kick_"))
async def clan_kick_handler(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    viewer_role = clan["role"] if clan else None
    if not clan or viewer_role not in ("owner", "moderator"):
        await callback.answer("Нет прав", show_alert=True)
        return
    target_id = int(callback.data.split("_")[2])
    members = await get_clan_members(clan["id"])
    target = next((m for m in members if m["user_id"] == target_id), None)
    if not target:
        await callback.answer("Участник не найден", show_alert=True)
        return
    if target["role"] == "owner":
        await callback.answer("Нельзя выгнать лидера", show_alert=True)
        return
    if viewer_role == "moderator" and target["role"] == "moderator":
        await callback.answer("Нет прав", show_alert=True)
        return
    name = target["first_name"] or target["username"] or f"id{target_id}"
    await kick_member(target_id, clan["id"])
    try:
        await callback.bot.send_message(
            target_id,
            f"👥 <b>{clan['name']}</b>\n\n🚫 Тебя исключили из клана.",
            parse_mode="HTML",
        )
    except Exception:
        pass
    members = await get_clan_members(clan["id"])
    text = (
        f"👥 <b>Участники клана {clan['name']}</b>\n\n"
        f"Всего: {len(members)}\n"
        "Нажми на участника чтобы управлять."
    )
    await safe_edit_text(callback.message, text, reply_markup=clan_members_kb(members, viewer_role))
    await callback.answer(f"🚫 {name} исключён")


@router.callback_query(F.data.startswith("clan_setmod_"))
async def clan_setmod_handler(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] != "owner":
        await callback.answer("Нет прав", show_alert=True)
        return
    target_id = int(callback.data.split("_")[2])
    members = await get_clan_members(clan["id"])
    target = next((m for m in members if m["user_id"] == target_id), None)
    if not target or target["role"] != "member":
        await callback.answer("Нельзя", show_alert=True)
        return
    name = target["first_name"] or target["username"] or f"id{target_id}"
    await set_member_role(target_id, clan["id"], "moderator")
    try:
        await callback.bot.send_message(
            target_id,
            f"👥 <b>{clan['name']}</b>\n\n🛡 Тебе назначена роль <b>Модератор</b>!",
            parse_mode="HTML",
        )
    except Exception:
        pass
    members = await get_clan_members(clan["id"])
    text = (
        f"👥 <b>Участники клана {clan['name']}</b>\n\n"
        f"Всего: {len(members)}\n"
        "Нажми на участника чтобы управлять."
    )
    await safe_edit_text(callback.message, text, reply_markup=clan_members_kb(members, "owner"))
    await callback.answer(f"🛡 {name} — теперь модератор")


@router.callback_query(F.data.startswith("clan_unsetmod_"))
async def clan_unsetmod_handler(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] != "owner":
        await callback.answer("Нет прав", show_alert=True)
        return
    target_id = int(callback.data.split("_")[2])
    members = await get_clan_members(clan["id"])
    target = next((m for m in members if m["user_id"] == target_id), None)
    if not target or target["role"] != "moderator":
        await callback.answer("Нельзя", show_alert=True)
        return
    name = target["first_name"] or target["username"] or f"id{target_id}"
    await set_member_role(target_id, clan["id"], "member")
    try:
        await callback.bot.send_message(
            target_id,
            f"👥 <b>{clan['name']}</b>\n\nРоль модератора снята.",
            parse_mode="HTML",
        )
    except Exception:
        pass
    members = await get_clan_members(clan["id"])
    text = (
        f"👥 <b>Участники клана {clan['name']}</b>\n\n"
        f"Всего: {len(members)}\n"
        "Нажми на участника чтобы управлять."
    )
    await safe_edit_text(callback.message, text, reply_markup=clan_members_kb(members, "owner"))
    await callback.answer(f"🧑 {name} — роль снята")


@router.callback_query(F.data == "clan_create")
async def clan_create_start(callback: CallbackQuery, state: FSMContext):
    clan = await get_user_clan(callback.from_user.id)
    if clan:
        await callback.answer("Ты уже в клане", show_alert=True)
        return
    await state.set_state(ClanCreate.waiting_name)
    await safe_edit_text(
        callback.message,
        "➕ <b>Создание клана</b>\n\nВведи <b>название</b> клана (3–20 символов):",
        reply_markup=clan_cancel_kb(),
    )
    await callback.answer()


@router.message(ClanCreate.waiting_name)
async def clan_create_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not (3 <= len(name) <= 20):
        await message.answer("❗ Название должно быть от 3 до 20 символов.", reply_markup=clan_cancel_kb())
        return
    if await get_clan_by_name(name):
        await message.answer("❗ Клан с таким названием уже существует.", reply_markup=clan_cancel_kb())
        return
    await state.update_data(clan_name=name)
    await state.set_state(ClanCreate.waiting_tag)
    await message.answer(
        f"Название: <b>{name}</b>\n\nТеперь введи <b>тег</b> клана (2–5 букв, только латиница):\n"
        "Тег используется для вступления друзей.",
        parse_mode="HTML",
        reply_markup=clan_cancel_kb(),
    )


@router.message(ClanCreate.waiting_tag)
async def clan_create_tag(message: Message, state: FSMContext):
    tag = message.text.strip().upper()
    if not (2 <= len(tag) <= 5) or not tag.isalpha():
        await message.answer("❗ Тег: 2–5 латинских букв.", reply_markup=clan_cancel_kb())
        return
    if await get_clan_by_tag(tag):
        await message.answer("❗ Тег уже занят, выбери другой.", reply_markup=clan_cancel_kb())
        return
    data = await state.get_data()
    await state.clear()
    clan = await create_clan(message.from_user.id, data["clan_name"], tag)
    await message.answer(
        f"✅ Клан <b>{clan['name']}</b> создан!\n\nТег для вступления: <code>{clan['tag']}</code>\n\n"
        "Поделись тегом с друзьями — они смогут вступить.",
        parse_mode="HTML",
        reply_markup=clan_menu_in_clan(role="owner", server_label=None),
    )


@router.callback_query(F.data == "clan_join")
async def clan_join_start(callback: CallbackQuery, state: FSMContext):
    clan = await get_user_clan(callback.from_user.id)
    if clan:
        await callback.answer("Ты уже в клане", show_alert=True)
        return
    await state.set_state(ClanJoin.waiting_tag)
    await safe_edit_text(
        callback.message,
        "🔑 <b>Вступить в клан</b>\n\nВведи <b>тег</b> клана:",
        reply_markup=clan_cancel_kb(),
    )
    await callback.answer()


@router.message(ClanJoin.waiting_tag)
async def clan_join_tag(message: Message, state: FSMContext):
    tag = message.text.strip().upper()
    clan = await get_clan_by_tag(tag)
    if not clan:
        await message.answer("❗ Клан с таким тегом не найден.", reply_markup=clan_cancel_kb())
        return
    existing = await get_user_clan(message.from_user.id)
    if existing:
        await message.answer("❗ Ты уже состоишь в клане.")
        await state.clear()
        return
    members = await get_clan_members(clan["id"])
    if len(members) >= MAX_CLAN_MEMBERS:
        await message.answer(
            f"❗ Клан заполнен ({len(members)}/{MAX_CLAN_MEMBERS}).",
            reply_markup=clan_cancel_kb(),
        )
        return
    await join_clan(message.from_user.id, clan["id"])
    await state.clear()
    server_label = await _build_server_label(clan["id"])
    joiner_name = message.from_user.first_name or message.from_user.username or f"id{message.from_user.id}"
    await message.answer(
        f"✅ Ты вступил в клан <b>{clan['name']}</b>!",
        parse_mode="HTML",
        reply_markup=clan_menu_in_clan(role="member", server_label=server_label),
    )
    bot: Bot = message.bot
    members = await get_clan_members(clan["id"])
    for m in members:
        if m["user_id"] == message.from_user.id:
            continue
        try:
            await bot.send_message(
                m["user_id"],
                f"👥 <b>{clan['name']}</b>\n\n"
                f"🟢 <b>{joiner_name}</b> вступил в клан!",
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.callback_query(F.data == "clan_leave")
async def clan_leave_handler(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    if not clan:
        await callback.answer("Ты не в клане", show_alert=True)
        return
    await leave_clan(callback.from_user.id)
    await safe_edit_text(
        callback.message,
        "👥 <b>Клан</b>\n\nТы покинул клан.\n\nВыбери действие ниже 👇",
        reply_markup=clan_menu_no_clan(),
    )
    await callback.answer("🚪 Ты покинул клан")


@router.callback_query(F.data == "clan_disband_confirm")
async def clan_disband_confirm(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] != "owner":
        await callback.answer("Нет прав", show_alert=True)
        return
    await safe_edit_text(
        callback.message,
        f"⚠️ <b>Распустить клан {clan['name']}?</b>\n\n"
        "Все участники будут исключены. Это действие нельзя отменить.",
        reply_markup=clan_disband_confirm_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "clan_disband")
async def clan_disband_handler(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] != "owner":
        await callback.answer("Нет прав", show_alert=True)
        return
    await leave_clan(callback.from_user.id)
    await safe_edit_text(
        callback.message,
        "👥 <b>Клан</b>\n\nКлан распущен.\n\nВыбери действие ниже 👇",
        reply_markup=clan_menu_no_clan(),
    )
    await callback.answer("🗑 Клан распущен")


# ─── НАЛАШТУВАННЯ КЛАНУ ──────────────────────────────────────────────────────

@router.callback_query(F.data == "clan_settings")
async def clan_settings_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        await callback.answer("Нет прав", show_alert=True)
        return
    is_owner = clan["role"] == "owner"
    photo = await get_clan_photo(clan["id"])
    text = (
        f"⚙️ <b>Настройки клана {clan['name']}</b>\n\n"
        f"{'🖼 Фото установлено.' if photo else '📷 Фото не установлено.'}"
    )
    await safe_edit_text(callback.message, text, reply_markup=clan_settings_kb(has_photo=bool(photo), is_owner=is_owner))
    await callback.answer()


@router.callback_query(F.data == "clan_photo_set")
async def clan_photo_set(callback: CallbackQuery, state: FSMContext):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        await callback.answer("Нет прав", show_alert=True)
        return
    await state.set_state(ClanSettings.waiting_photo)
    await safe_edit_text(
        callback.message,
        "🖼 Отправь фото для клана.\nОно будет показываться при открытии страницы клана.",
        reply_markup=clan_photo_cancel_kb(),
    )
    await callback.answer()


@router.message(ClanSettings.waiting_photo, F.photo)
async def clan_photo_receive(message: Message, state: FSMContext):
    clan = await get_user_clan(message.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        return
    file_id = message.photo[-1].file_id
    await set_clan_photo(clan["id"], file_id)
    await state.clear()
    await message.answer(
        f"✅ Фото клана <b>{clan['name']}</b> установлено!",
        parse_mode="HTML",
        reply_markup=clan_settings_kb(has_photo=True, is_owner=clan["role"] == "owner"),
    )


@router.message(ClanSettings.waiting_photo)
async def clan_photo_wrong(message: Message):
    await message.answer("❗ Нужно отправить фото.", reply_markup=clan_photo_cancel_kb())


@router.callback_query(F.data == "clan_photo_del")
async def clan_photo_delete(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        await callback.answer("Нет прав", show_alert=True)
        return
    await delete_clan_photo(clan["id"])
    await safe_edit_text(
        callback.message,
        f"⚙️ <b>Настройки клана {clan['name']}</b>\n\n📷 Фото не установлено.",
        reply_markup=clan_settings_kb(has_photo=False, is_owner=clan["role"] == "owner"),
    )
    await callback.answer("🗑 Фото удалено")


# ─── ПЕРЕЙМЕНУВАННЯ ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "clan_rename")
async def clan_rename_start(callback: CallbackQuery, state: FSMContext):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        await callback.answer("Нет прав", show_alert=True)
        return
    await state.set_state(ClanSettings.waiting_new_name)
    await safe_edit_text(
        callback.message,
        f"✏️ <b>Изменить название клана</b>\n\nТекущее: <b>{clan['name']}</b>\n\nВведи новое название:",
        reply_markup=clan_photo_cancel_kb(),
    )
    await callback.answer()


@router.message(ClanSettings.waiting_new_name)
async def clan_rename_receive(message: Message, state: FSMContext):
    clan = await get_user_clan(message.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        await state.clear()
        return
    new_name = message.text.strip()
    if len(new_name) < 2 or len(new_name) > 32:
        await message.answer("❗ Название должно быть от 2 до 32 символов.", reply_markup=clan_photo_cancel_kb())
        return
    await rename_clan(clan["id"], new_name)
    await state.clear()
    photo = await get_clan_photo(clan["id"])
    await message.answer(
        f"✅ Название изменено на <b>{new_name}</b>!",
        parse_mode="HTML",
        reply_markup=clan_settings_kb(has_photo=bool(photo), is_owner=clan["role"] == "owner"),
    )


@router.callback_query(F.data == "clan_retag")
async def clan_retag_start(callback: CallbackQuery, state: FSMContext):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        await callback.answer("Нет прав", show_alert=True)
        return
    await state.set_state(ClanSettings.waiting_new_tag)
    await safe_edit_text(
        callback.message,
        f"🏷 <b>Изменить тег клана</b>\n\nТекущий: <b>{clan['tag']}</b>\n\nВведи новый тег (2–6 букв):",
        reply_markup=clan_photo_cancel_kb(),
    )
    await callback.answer()


@router.message(ClanSettings.waiting_new_tag)
async def clan_retag_receive(message: Message, state: FSMContext):
    clan = await get_user_clan(message.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        await state.clear()
        return
    new_tag = message.text.strip().upper()
    if not new_tag.isalpha() or len(new_tag) < 2 or len(new_tag) > 6:
        await message.answer("❗ Тег: только буквы, от 2 до 6 символов.", reply_markup=clan_photo_cancel_kb())
        return
    await retag_clan(clan["id"], new_tag)
    await state.clear()
    photo = await get_clan_photo(clan["id"])
    await message.answer(
        f"✅ Тег изменён на <b>{new_tag}</b>!",
        parse_mode="HTML",
        reply_markup=clan_settings_kb(has_photo=bool(photo), is_owner=clan["role"] == "owner"),
    )


# ─── СЕРВЕР КЛАНА ────────────────────────────────────────────────────────────

async def _clan_server_text(clan: dict, server_id: int | None = None) -> str:
    if server_id is None:
        server_id = await get_clan_server_id(clan["id"])
    if not server_id:
        return "🖥 <b>Сервер клана</b>\n\nСервер не выбран."
    server = await get_server(server_id)
    if not server:
        await remove_clan_server(clan["id"])
        return "🖥 <b>Сервер клана</b>\n\nСервер был удалён. Выбери новый."
    countdown = format_countdown(server["hours_left"])
    return (
        f"🖥 <b>Сервер клана: {server['name']}</b>\n\n"
        f"⏱ До вайпа: <b>{countdown}</b>"
    )


@router.callback_query(F.data == "clan_server")
async def clan_server_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    clan = await get_user_clan(callback.from_user.id)
    if not clan:
        await callback.answer("Ты не в клане", show_alert=True)
        return
    is_manager = clan["role"] in ("owner", "moderator")
    server_id = await get_clan_server_id(clan["id"])
    text = await _clan_server_text(clan)
    await safe_edit_text(
        callback.message,
        text,
        reply_markup=clan_server_kb(is_manager=is_manager, has_server=bool(server_id)),
    )
    await callback.answer()


@router.callback_query(F.data == "clan_server_pick")
async def clan_server_pick(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        await callback.answer("Нет прав", show_alert=True)
        return
    servers = await get_servers(callback.from_user.id)
    if not servers:
        await callback.answer("У тебя нет серверов. Создай через меню вайпа.", show_alert=True)
        return
    await safe_edit_text(
        callback.message,
        "📋 <b>Выбери сервер для клана</b>\n\nОн будет виден всем участникам.",
        reply_markup=clan_server_pick_kb(servers),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("clan_server_use_"))
async def clan_server_use(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        await callback.answer("Нет прав", show_alert=True)
        return
    server_id = int(callback.data.split("_")[3])
    server = await get_server(server_id)
    if not server:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await set_clan_server(clan["id"], server_id)
    text = await _clan_server_text(clan, server_id=server_id)
    await safe_edit_text(
        callback.message,
        text,
        reply_markup=clan_server_kb(is_manager=True, has_server=True),
    )
    await callback.answer(f"✅ Сервер {server['name']} установлен")


@router.callback_query(F.data == "clan_server_remove")
async def clan_server_remove(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        await callback.answer("Нет прав", show_alert=True)
        return
    await remove_clan_server(clan["id"])
    await safe_edit_text(
        callback.message,
        "🖥 <b>Сервер клана</b>\n\nСервер не выбран.",
        reply_markup=clan_server_kb(is_manager=True, has_server=False),
    )
    await callback.answer("❌ Сервер убран")


# ─── СТВОРИТИ НОВИЙ СЕРВЕР З КЛАНУ ──────────────────────────────────────────

@router.callback_query(F.data == "clan_server_new")
async def clan_server_new(callback: CallbackQuery, state: FSMContext):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        await callback.answer("Нет прав", show_alert=True)
        return
    await state.set_state(ClanServerAdd.wipe_type)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🆕 Новый вайп", callback_data="clan_srv_type_new"),
        InlineKeyboardButton(text="⏳ Вайп идёт", callback_data="clan_srv_type_old"),
    )
    builder.row(InlineKeyboardButton(text="🔜 Вайп скоро", callback_data="clan_srv_type_pending"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="clan_server"))
    await safe_edit_text(
        callback.message,
        "➕ <b>Добавить сервер клана</b>\n\nВыбери тип вайпа:",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(ClanServerAdd.wipe_type, F.data.in_({"clan_srv_type_new", "clan_srv_type_old", "clan_srv_type_pending"}))
async def clan_srv_type(callback: CallbackQuery, state: FSMContext):
    wtype = callback.data.split("_")[-1]
    labels = {"new": "🆕 Новый вайп", "old": "⏳ Вайп идёт", "pending": "🔜 Вайп скоро"}
    await state.update_data(wipe_type=wtype)
    await state.set_state(ClanServerAdd.name)
    await safe_edit_text(
        callback.message,
        f"{labels[wtype]}\n\nВведи <b>название сервера</b>:\n<i>Например: CEO-734</i>",
        reply_markup=clan_server_cancel_kb(),
    )
    await callback.answer()


@router.message(ClanServerAdd.name)
async def clan_srv_name(message: Message, state: FSMContext):
    name = message.text.strip()
    data = await state.get_data()
    wtype = data["wipe_type"]
    await state.update_data(name=name)

    if wtype == "new":
        server_id = await add_server(message.from_user.id, name, WIPE_DURATION_HOURS)
        clan = await get_user_clan(message.from_user.id)
        await set_clan_server(clan["id"], server_id)
        await state.clear()
        text = await _clan_server_text(clan, server_id=server_id)
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=clan_server_kb(is_manager=True, has_server=True),
        )
    elif wtype == "old":
        await state.set_state(ClanServerAdd.hours)
        await message.answer(
            f"⏳ <b>{name}</b>\n\nСколько часов осталось до вайпа?",
            parse_mode="HTML",
            reply_markup=clan_server_cancel_kb(),
        )
    else:
        await state.set_state(ClanServerAdd.pending_hours)
        await message.answer(
            f"🔜 <b>{name}</b>\n\nЧерез сколько часов начнётся вайп?",
            parse_mode="HTML",
            reply_markup=clan_server_cancel_kb(),
        )


@router.message(ClanServerAdd.hours)
async def clan_srv_hours(message: Message, state: FSMContext):
    try:
        hours = parse_hours_input(message.text)
    except (ValueError, IndexError):
        await message.answer("❗ Введи число.\n<i>Например: 120 или 1:30</i>", parse_mode="HTML", reply_markup=clan_server_cancel_kb())
        return
    data = await state.get_data()
    server_id = await add_server(message.from_user.id, data["name"], hours)
    clan = await get_user_clan(message.from_user.id)
    await set_clan_server(clan["id"], server_id)
    await state.clear()
    text = await _clan_server_text(clan, server_id=server_id)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=clan_server_kb(is_manager=True, has_server=True),
    )


@router.message(ClanServerAdd.pending_hours)
async def clan_srv_pending(message: Message, state: FSMContext):
    try:
        hours = parse_hours_input(message.text)
    except (ValueError, IndexError):
        await message.answer("❗ Введи число.\n<i>Например: 12 или 1:30</i>", parse_mode="HTML", reply_markup=clan_server_cancel_kb())
        return
    data = await state.get_data()
    server_id = await add_server(message.from_user.id, data["name"], hours + WIPE_DURATION_HOURS, had_pending=True)
    clan = await get_user_clan(message.from_user.id)
    await set_clan_server(clan["id"], server_id)
    await state.clear()
    text = await _clan_server_text(clan, server_id=server_id)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=clan_server_kb(is_manager=True, has_server=True),
    )
