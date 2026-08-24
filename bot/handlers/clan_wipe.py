from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.nav import safe_edit_text
from data.models_clan import get_user_clan, get_clan_server_id, set_clan_server
from data.models_clan_loot import get_clan_loot_events
from data.models_wipe import (
    get_server, get_servers, add_server, update_server_hours,
    set_active_server, format_countdown, format_hours,
    parse_hours_input, WIPE_DURATION_HOURS,
)
from data.models_loot import format_time_left
from states.states_wipe import ClanAddServer, ClanQuickStart

router = Router()

_EVENT_LABELS = {
    "tank":    '<tg-emoji emoji-id="5325863428198265230">🚗</tg-emoji> Танк',
    "avenger": '<tg-emoji emoji-id="5341780894824831113">😈</tg-emoji> Мститель',
    "egg":     '<tg-emoji emoji-id="5341313306030283326">🥚</tg-emoji> Монст Егг',
    "heli":    '<tg-emoji emoji-id="5323546495205536651">🚁</tg-emoji> Вертолет',
    "patrol":  '<tg-emoji emoji-id="5386642223368530459">🪂</tg-emoji> Десант',
    "cargo":   '<tg-emoji emoji-id="5323526957399308323">🚢</tg-emoji> Карго',
    "room":    "📦 Комната",
}


# ─── КЛАВІАТУРИ ──────────────────────────────────────────────────────────────

def _leader_main_kb(clan_srv: dict | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if clan_srv:
        countdown = format_countdown(clan_srv["hours_left"])
        builder.row(InlineKeyboardButton(
            text=f"✅ {clan_srv['name']} — {countdown}",
            callback_data=f"cwipe_srv_{clan_srv['id']}",
        ))
    builder.row(
        InlineKeyboardButton(text="➕ Добавить сервер", callback_data="cwipe_add"),
        InlineKeyboardButton(text="📋 Мои серверы",     callback_data="cwipe_servers"),
    )
    builder.row(InlineKeyboardButton(text="🚀 Старт нового вайпа", callback_data="cwipe_quickstart"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def _servers_list_kb(servers: list[dict], clan_srv_id: int | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in servers:
        mark = "✅ " if s["id"] == clan_srv_id else ""
        countdown = format_countdown(s["hours_left"])
        builder.row(InlineKeyboardButton(
            text=f"{mark}🧹 {s['name']} — {countdown}",
            callback_data=f"cwipe_srv_{s['id']}",
        ))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="clan_wipe"))
    return builder.as_markup()


def _server_profile_kb(server_id: int, is_clan: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_clan:
        builder.row(InlineKeyboardButton(
            text="⭐ Установить для клана",
            callback_data=f"cwipe_setclan_{server_id}",
        ))
    else:
        builder.row(InlineKeyboardButton(text="✅ Сервер клана", callback_data="noop"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="cwipe_servers"))
    return builder.as_markup()


def _cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="clan_wipe"))
    return builder.as_markup()


def _type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🆕 Новый вайп",  callback_data="cwipe_type_new"),
        InlineKeyboardButton(text="⏳ Старый вайп", callback_data="cwipe_type_old"),
    )
    builder.row(InlineKeyboardButton(text="🔜 Вайп ещё не начался", callback_data="cwipe_type_pending"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="clan_wipe"))
    return builder.as_markup()


def _member_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="clan_wipe"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад",    callback_data="main_menu"))
    return builder.as_markup()


# ─── ГОЛОВНИЙ ХЕНДЛЕР ────────────────────────────────────────────────────────

@router.callback_query(F.data == "clan_wipe")
async def clan_wipe_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    clan = await get_user_clan(callback.from_user.id)
    if not clan:
        await callback.answer("Ты не в клане", show_alert=True)
        return

    is_leader = clan["owner_id"] == callback.from_user.id
    srv_id = await get_clan_server_id(clan["id"])
    clan_srv = await get_server(srv_id) if srv_id else None

    if is_leader:
        text = (
            f"🧹 <b>Вайп клана {clan['name']}</b>\n\n"
            "<blockquote>Добавь или выбери сервер клана — все участники будут видеть таймер вайпа.</blockquote>"
        )
        await safe_edit_text(callback.message, text, reply_markup=_leader_main_kb(clan_srv))
    else:
        if not clan_srv:
            await callback.answer("Лидер ещё не выбрал сервер клана", show_alert=True)
            return
        countdown = format_countdown(clan_srv["hours_left"])
        text = f"🧹 <b>Вайп клана {clan['name']}</b>\n\n⏱ {clan_srv['name']} — <b>{countdown}</b>\n"
        events = await get_clan_loot_events(clan["id"])
        if events:
            text += "\n<b>Что залутали:</b>\n"
            for e in events:
                name = e["first_name"] or e["username"] or f"id{e['user_id']}"
                label = _EVENT_LABELS.get(e["event_name"], e["event_name"])
                time_left = format_time_left(e["seconds_left"])
                text += f"• {name} — {label} ⏳ {time_left}\n"
        else:
            text += "\n<i>Никто ещё ничего не залутал.</i>"
        await safe_edit_text(callback.message, text, reply_markup=_member_kb())

    await callback.answer()


# ─── СПИСОК СЕРВЕРІВ ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "cwipe_servers")
async def cwipe_servers(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["owner_id"] != callback.from_user.id:
        await callback.answer("Только лидер может управлять сервером клана", show_alert=True)
        return
    servers = await get_servers(callback.from_user.id)
    srv_id = await get_clan_server_id(clan["id"])
    text = "📋 <b>Мои серверы</b>\n\nВыбери сервер для клана:" if servers else "📋 У тебя нет серверов. Добавь новый!"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_servers_list_kb(servers, srv_id))
    await callback.answer()


@router.callback_query(F.data.startswith("cwipe_srv_"))
async def cwipe_srv_profile(callback: CallbackQuery):
    server_id = int(callback.data.split("_")[2])
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["owner_id"] != callback.from_user.id:
        await callback.answer("Только лидер", show_alert=True)
        return
    s = await get_server(server_id)
    if not s:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    srv_id = await get_clan_server_id(clan["id"])
    is_clan = (srv_id == server_id)
    countdown = format_countdown(s["hours_left"])
    text = f"🧹 <b>{s['name']}</b>\n\n⏱ До вайпа: <b>{countdown}</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_server_profile_kb(server_id, is_clan))
    await callback.answer()


@router.callback_query(F.data.startswith("cwipe_setclan_"))
async def cwipe_setclan(callback: CallbackQuery):
    server_id = int(callback.data.split("_")[2])
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["owner_id"] != callback.from_user.id:
        await callback.answer("Только лидер", show_alert=True)
        return
    s = await get_server(server_id)
    if not s:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await set_clan_server(clan["id"], server_id)
    countdown = format_countdown(s["hours_left"])
    text = f"🧹 <b>{s['name']}</b>\n\n⏱ До вайпа: <b>{countdown}</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_server_profile_kb(server_id, is_clan=True))
    await callback.answer(f"✅ {s['name']} — сервер клана!", show_alert=True)


# ─── QUICKSTART ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "cwipe_quickstart")
async def cwipe_quickstart_begin(callback: CallbackQuery, state: FSMContext):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["owner_id"] != callback.from_user.id:
        await callback.answer("Только лидер", show_alert=True)
        return
    await state.set_state(ClanQuickStart.name)
    await callback.message.edit_text(
        "🚀 <b>Старт нового вайпа клана</b>\n\nКак называется сервер?\n<i>Например: Европа 549</i>",
        parse_mode="HTML",
        reply_markup=_cancel_kb(),
    )
    await callback.answer()


@router.message(ClanQuickStart.name)
async def cwipe_quickstart_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(ClanQuickStart.hours)
    await message.answer(
        "⏳ Через сколько часов начнётся вайп?\n\n<i>Например: 2 или 1:30</i>",
        parse_mode="HTML",
        reply_markup=_cancel_kb(),
    )


@router.message(ClanQuickStart.hours)
async def cwipe_quickstart_hours(message: Message, state: FSMContext):
    try:
        hours = parse_hours_input(message.text)
    except (ValueError, IndexError):
        await message.answer("❗ Введи число или время.\n<i>Например: 2 или 1:30</i>", parse_mode="HTML", reply_markup=_cancel_kb())
        return
    data = await state.get_data()
    name = data["name"]
    clan = await get_user_clan(message.from_user.id)
    server_id = await add_server(message.from_user.id, name, hours + WIPE_DURATION_HOURS, had_pending=True)
    await set_active_server(message.from_user.id, server_id)
    await set_clan_server(clan["id"], server_id)
    await state.clear()
    clan_srv = await get_server(server_id)
    await message.answer(
        f"✅ <b>{name}</b> — сервер клана!\n⏳ Вайп через <b>{format_hours(hours)}</b>",
        parse_mode="HTML",
        reply_markup=_leader_main_kb(clan_srv),
    )


# ─── ДОДАТИ СЕРВЕР ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "cwipe_add")
async def cwipe_add_start(callback: CallbackQuery, state: FSMContext):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["owner_id"] != callback.from_user.id:
        await callback.answer("Только лидер", show_alert=True)
        return
    await state.set_state(ClanAddServer.wipe_type)
    await callback.message.edit_text(
        "➕ <b>Добавить сервер клана</b>\n\nВыбери тип вайпа:",
        parse_mode="HTML",
        reply_markup=_type_kb(),
    )
    await callback.answer()


@router.callback_query(ClanAddServer.wipe_type, F.data == "cwipe_type_new")
async def cwipe_type_new(callback: CallbackQuery, state: FSMContext):
    await state.update_data(wipe_type="new")
    await state.set_state(ClanAddServer.name)
    await callback.message.edit_text(
        "🆕 <b>Новый вайп</b>\n\nВведи название сервера:\n<i>Например: CEO-734</i>",
        parse_mode="HTML",
        reply_markup=_cancel_kb(),
    )
    await callback.answer()


@router.callback_query(ClanAddServer.wipe_type, F.data == "cwipe_type_old")
async def cwipe_type_old(callback: CallbackQuery, state: FSMContext):
    await state.update_data(wipe_type="old")
    await state.set_state(ClanAddServer.name)
    await callback.message.edit_text(
        "⏳ <b>Старый вайп</b>\n\nВведи название сервера:\n<i>Например: CEO-734</i>",
        parse_mode="HTML",
        reply_markup=_cancel_kb(),
    )
    await callback.answer()


@router.callback_query(ClanAddServer.wipe_type, F.data == "cwipe_type_pending")
async def cwipe_type_pending(callback: CallbackQuery, state: FSMContext):
    await state.update_data(wipe_type="pending")
    await state.set_state(ClanAddServer.name)
    await callback.message.edit_text(
        "🔜 <b>Вайп ещё не начался</b>\n\nВведи название сервера:\n<i>Например: CEO-734</i>",
        parse_mode="HTML",
        reply_markup=_cancel_kb(),
    )
    await callback.answer()


@router.message(ClanAddServer.name)
async def cwipe_add_name(message: Message, state: FSMContext):
    name = message.text.strip()
    data = await state.get_data()
    await state.update_data(name=name)
    wipe_type = data["wipe_type"]

    if wipe_type == "new":
        clan = await get_user_clan(message.from_user.id)
        server_id = await add_server(message.from_user.id, name, WIPE_DURATION_HOURS)
        await set_active_server(message.from_user.id, server_id)
        await set_clan_server(clan["id"], server_id)
        await state.clear()
        clan_srv = await get_server(server_id)
        await message.answer(
            f"✅ <b>{name}</b> — сервер клана!\n⏱ До вайпа: <b>{WIPE_DURATION_HOURS} ч.</b>",
            parse_mode="HTML",
            reply_markup=_leader_main_kb(clan_srv),
        )
    elif wipe_type == "old":
        await state.set_state(ClanAddServer.hours)
        await message.answer(
            f"⏳ Сервер <b>{name}</b>\n\nСколько часов осталось до вайпа?\n<i>Например: 120</i>",
            parse_mode="HTML",
            reply_markup=_cancel_kb(),
        )
    elif wipe_type == "pending":
        await state.set_state(ClanAddServer.pending_hours)
        await message.answer(
            f"🔜 Сервер <b>{name}</b>\n\nЧерез сколько часов начнётся вайп?\n<i>Например: 12</i>",
            parse_mode="HTML",
            reply_markup=_cancel_kb(),
        )


@router.message(ClanAddServer.hours)
async def cwipe_add_hours(message: Message, state: FSMContext):
    try:
        hours = parse_hours_input(message.text)
    except (ValueError, IndexError):
        await message.answer("❗ Введи число или время.\n<i>Например: 120 или 1:30</i>", parse_mode="HTML", reply_markup=_cancel_kb())
        return
    data = await state.get_data()
    clan = await get_user_clan(message.from_user.id)
    server_id = await add_server(message.from_user.id, data["name"], hours)
    await set_active_server(message.from_user.id, server_id)
    await set_clan_server(clan["id"], server_id)
    await state.clear()
    clan_srv = await get_server(server_id)
    await message.answer(
        f"✅ <b>{data['name']}</b> — сервер клана!\n⏱ До вайпа: <b>{hours:.0f} ч.</b>",
        parse_mode="HTML",
        reply_markup=_leader_main_kb(clan_srv),
    )


@router.message(ClanAddServer.pending_hours)
async def cwipe_add_pending_hours(message: Message, state: FSMContext):
    try:
        hours = parse_hours_input(message.text)
    except (ValueError, IndexError):
        await message.answer("❗ Введи число или время.\n<i>Например: 12 или 1:30</i>", parse_mode="HTML", reply_markup=_cancel_kb())
        return
    data = await state.get_data()
    clan = await get_user_clan(message.from_user.id)
    server_id = await add_server(message.from_user.id, data["name"], hours + WIPE_DURATION_HOURS, had_pending=True)
    await set_active_server(message.from_user.id, server_id)
    await set_clan_server(clan["id"], server_id)
    await state.clear()
    clan_srv = await get_server(server_id)
    await message.answer(
        f"✅ <b>{data['name']}</b> — сервер клана!\n"
        f"🔜 Вайп через <b>{hours:.0f} ч.</b> — потом <b>{WIPE_DURATION_HOURS} ч.</b>",
        parse_mode="HTML",
        reply_markup=_leader_main_kb(clan_srv),
    )
