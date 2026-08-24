from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from data.models_wipe import get_servers, get_server, add_server, update_server_hours, delete_server, set_active_server, get_active_server, format_countdown, format_hours, parse_hours_input, WIPE_DURATION_HOURS
from bot.wipe.keyboards_main import wipe_cancel_kb, wipe_main_kb
from bot.wipe.keyboards_servers import servers_list_kb, server_profile_kb, edit_cancel_kb, wipe_type_kb
from states.states_wipe import AddServer, EditServer, QuickStart

router = Router()

WIPE_HOURS_NEW = WIPE_DURATION_HOURS


@router.callback_query(F.data == "wipe_servers")
async def show_servers(callback: CallbackQuery):
    servers = await get_servers(callback.from_user.id)
    text = "📋 <b>Мои серверы</b>\n\n" + ("Выбери сервер:" if servers else "У тебя пока нет добавленных серверов.")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=servers_list_kb(servers))
    await callback.answer()


@router.callback_query(F.data.startswith("wipe_server_"))
async def server_profile(callback: CallbackQuery):
    server_id = int(callback.data.split("_")[2])
    s = await get_server(server_id)
    if not s:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    countdown = format_countdown(s["hours_left"])
    text = f"🧹 <b>{s['name']}</b>\n\n⏱ До вайпа: <b>{countdown}</b>"
    is_active = bool(s.get("is_active"))
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=server_profile_kb(server_id, is_active))
    await callback.answer()


@router.callback_query(F.data.startswith("wipe_setactive_"))
async def set_active_handler(callback: CallbackQuery):
    server_id = int(callback.data.split("_")[2])
    s = await get_server(server_id)
    if not s:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await set_active_server(callback.from_user.id, server_id)
    s = await get_server(server_id)
    countdown = format_countdown(s["hours_left"])
    text = f"🧹 <b>{s['name']}</b>\n\n⏱ До вайпа: <b>{countdown}</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=server_profile_kb(server_id, is_active=True))
    await callback.answer(f"✅ {s['name']} теперь активный сервер", show_alert=True)


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()


# ─── СТАРТ НОВОГО ВАЙПА ──────────────────────────────────────────────────────

@router.callback_query(F.data == "wipe_quickstart")
async def quickstart_begin(callback: CallbackQuery, state: FSMContext):
    await state.set_state(QuickStart.name)
    await callback.message.edit_text(
        "🚀 <b>Старт нового вайпа</b>\n\n"
        "Только что прошёл вайп? Бот запомнит таймер и будет напоминать о луте и событиях.\n\n"
        "Как называется твой сервер?\n"
        "<i>Например: Европа 355</i>",
        parse_mode="HTML",
        reply_markup=wipe_cancel_kb(),
    )
    await callback.answer()


@router.message(QuickStart.name)
async def quickstart_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(QuickStart.hours)
    await message.answer(
        "⏳ Через сколько часов начнётся вайп?\n\n"
        "<i>Можно написать:\n"
        "• <b>2</b> — через 2 часа\n"
        "• <b>1:30</b> — через 1 час 30 минут</i>",
        parse_mode="HTML",
        reply_markup=wipe_cancel_kb(),
    )


@router.message(QuickStart.hours)
async def quickstart_hours(message: Message, state: FSMContext):
    try:
        hours = parse_hours_input(message.text)
    except (ValueError, IndexError):
        await message.answer("❗ Введи число или время.\n<i>Например: 2 или 1:30</i>", parse_mode="HTML", reply_markup=wipe_cancel_kb())
        return
    data = await state.get_data()
    name = data["name"]
    server_id = await add_server(message.from_user.id, name, hours + WIPE_DURATION_HOURS, had_pending=True)
    await set_active_server(message.from_user.id, server_id)
    await state.clear()
    active = await get_active_server(message.from_user.id)
    await message.answer(
        f"✅ <b>{name}</b> добавлен!\n"
        f"⏳ Вайп начнётся через <b>{format_hours(hours)}</b> — бот следит за таймером.",
        parse_mode="HTML",
        reply_markup=wipe_main_kb(active),
    )


# ─── ДОДАТИ СЕРВЕР: крок 1 — тип вайпу ────────────────────────────────────

@router.callback_query(F.data == "wipe_add")
async def add_server_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddServer.wipe_type)
    await callback.message.edit_text(
        "➕ <b>Добавить сервер</b>\n\nВыбери тип вайпа:",
        parse_mode="HTML",
        reply_markup=wipe_type_kb(),
    )
    await callback.answer()


@router.callback_query(AddServer.wipe_type, F.data == "wipe_type_new")
async def type_new(callback: CallbackQuery, state: FSMContext):
    await state.update_data(wipe_type="new")
    await state.set_state(AddServer.name)
    await callback.message.edit_text(
        "🆕 <b>Новый вайп</b>\n\nВведи название сервера:\n<i>Например: CEO-734</i>",
        parse_mode="HTML",
        reply_markup=wipe_cancel_kb(),
    )
    await callback.answer()


@router.callback_query(AddServer.wipe_type, F.data == "wipe_type_old")
async def type_old(callback: CallbackQuery, state: FSMContext):
    await state.update_data(wipe_type="old")
    await state.set_state(AddServer.name)
    await callback.message.edit_text(
        "⏳ <b>Старый вайп</b>\n\nВведи название сервера:\n<i>Например: CEO-734</i>",
        parse_mode="HTML",
        reply_markup=wipe_cancel_kb(),
    )
    await callback.answer()


@router.callback_query(AddServer.wipe_type, F.data == "wipe_type_pending")
async def type_pending(callback: CallbackQuery, state: FSMContext):
    await state.update_data(wipe_type="pending")
    await state.set_state(AddServer.name)
    await callback.message.edit_text(
        "🔜 <b>Вайп ещё не начался</b>\n\nВведи название сервера:\n<i>Например: CEO-734</i>",
        parse_mode="HTML",
        reply_markup=wipe_cancel_kb(),
    )
    await callback.answer()


# ─── ДОДАТИ СЕРВЕР: крок 2 — назва ─────────────────────────────────────────

@router.message(AddServer.name)
async def add_server_name(message: Message, state: FSMContext):
    name = message.text.strip()
    data = await state.get_data()
    wipe_type = data["wipe_type"]
    await state.update_data(name=name)

    if wipe_type == "new":
        await add_server(message.from_user.id, name, WIPE_HOURS_NEW)
        await state.clear()
        await message.answer(
            f"✅ Вайп сервера <b>{name}</b> начат!\n"
            f"⏱ До следующего вайпа: <b>{WIPE_HOURS_NEW} ч.</b>",
            parse_mode="HTML",
            reply_markup=servers_list_kb(await get_servers(message.from_user.id)),
        )

    elif wipe_type == "old":
        await state.set_state(AddServer.hours)
        await message.answer(
            f"⏳ Сервер <b>{name}</b>\n\nСколько часов осталось до вайпа?\n<i>Например: 120</i>",
            parse_mode="HTML",
            reply_markup=wipe_cancel_kb(),
        )

    elif wipe_type == "pending":
        await state.set_state(AddServer.pending_hours)
        await message.answer(
            f"🔜 Сервер <b>{name}</b>\n\nЧерез сколько часов начнётся вайп?\n<i>Например: 12</i>",
            parse_mode="HTML",
            reply_markup=wipe_cancel_kb(),
        )


# ─── ДОДАТИ СЕРВЕР: крок 3 — години ─────────────────────────────────────────

@router.message(AddServer.hours)
async def add_server_hours(message: Message, state: FSMContext):
    try:
        hours = parse_hours_input(message.text)
    except (ValueError, IndexError):
        await message.answer("❗ Введи число или время.\n<i>Например: 120 или 1:30</i>", parse_mode="HTML", reply_markup=wipe_cancel_kb())
        return
    data = await state.get_data()
    await add_server(message.from_user.id, data["name"], hours)
    await state.clear()
    await message.answer(
        f"✅ Сервер <b>{data['name']}</b> добавлен!\n⏱ До вайпа: <b>{hours:.0f} ч.</b>",
        parse_mode="HTML",
        reply_markup=servers_list_kb(await get_servers(message.from_user.id)),
    )


@router.message(AddServer.pending_hours)
async def add_server_pending_hours(message: Message, state: FSMContext):
    try:
        hours = parse_hours_input(message.text)
    except (ValueError, IndexError):
        await message.answer("❗ Введи число или время.\n<i>Например: 12 или 1:30</i>", parse_mode="HTML", reply_markup=wipe_cancel_kb())
        return
    data = await state.get_data()
    await add_server(message.from_user.id, data["name"], hours + WIPE_HOURS_NEW, had_pending=True)
    await state.clear()
    await message.answer(
        f"✅ Сервер <b>{data['name']}</b> добавлен!\n"
        f"🔜 До вайпа: <b>{hours:.0f} ч.</b>\n"
        f"⏱ После вайпа: <b>{WIPE_HOURS_NEW} ч.</b>",
        parse_mode="HTML",
        reply_markup=servers_list_kb(await get_servers(message.from_user.id)),
    )


# ─── РЕДАГУВАТИ / ВИДАЛИТИ ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("wipe_edit_"))
async def edit_server_start(callback: CallbackQuery, state: FSMContext):
    server_id = int(callback.data.split("_")[2])
    s = await get_server(server_id)
    if not s:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await state.set_state(EditServer.hours)
    await state.update_data(server_id=server_id)
    await callback.message.edit_text(
        f"✏️ <b>{s['name']}</b>\n\nВведи новое количество часов до вайпа:\n<i>Например: 120</i>",
        parse_mode="HTML",
        reply_markup=edit_cancel_kb(server_id),
    )
    await callback.answer()


@router.message(EditServer.hours)
async def edit_server_hours(message: Message, state: FSMContext):
    try:
        hours = parse_hours_input(message.text)
    except (ValueError, IndexError):
        await message.answer("❗ Введи число или время.\n<i>Например: 120 или 1:30</i>", parse_mode="HTML")
        return
    data = await state.get_data()
    server_id = data["server_id"]
    await update_server_hours(server_id, hours)
    await state.clear()
    s = await get_server(server_id)
    is_active = bool(s.get("is_active"))
    await message.answer(
        f"✅ Обновлено!\n🧹 <b>{s['name']}</b> — <b>{hours:.0f} ч.</b>",
        parse_mode="HTML",
        reply_markup=server_profile_kb(server_id, is_active),
    )


@router.callback_query(F.data.startswith("wipe_delete_"))
async def delete_server_handler(callback: CallbackQuery):
    server_id = int(callback.data.split("_")[2])
    s = await get_server(server_id)
    if not s:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await delete_server(server_id)
    await callback.answer(f"❌ Сервер {s['name']} удалён", show_alert=True)
    servers = await get_servers(callback.from_user.id)
    text = "📋 <b>Мои серверы</b>\n\n" + ("Выбери сервер:" if servers else "У тебя пока нет добавленных серверов.")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=servers_list_kb(servers))
