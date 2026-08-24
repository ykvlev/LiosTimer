import asyncio

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.utils.nav import safe_edit_text
from bot.keyboards.loot_menu import (
    loot_menu, rooms_list_kb, location_kb, slot_kb,
    location_settings_main_kb, location_spawn_kb, cd_cancel_kb,
    location_cards_edit_kb, slot_edit_kb, loot_notify_choice_kb,
    event_settings_kb, event_cd_cancel_kb,
)
from bot.keyboards.tank_menu import tank_kb
from bot.keyboards.avenger_menu import avenger_kb
from bot.keyboards.egg_menu import egg_kb
from bot.keyboards.heli_menu import heli_kb
from bot.keyboards.patrol_menu import patrol_kb
from bot.keyboards.cargo_menu import cargo_kb
from bot.keyboards.medal_menu import medal_kb
from bot.keyboards.miniboss_menu import miniboss_kb
from data.models_miniboss import get_all_miniboss, mark_miniboss_looted, reset_miniboss, MINIBOSS_ROOMS
from data.models_loot import (
    LOCATIONS, DEFAULT_MINUTES, CARD_EMOJI, CARD_EMOJI_HTML, CARD_NAMES,
    LOOT_ITEM_LABELS, EVENT_DEFAULTS,
    get_all_slots, get_slot, set_card_type, mark_looted, reset_slot_timer,
    format_time_left, get_user_cd_minutes, set_user_cd_minutes, parse_hm, format_minutes,
    get_user_event_cd, set_user_event_cd,
)
from data.models_tank import get_tank, get_tank_status, mark_tank_looted, reset_tank, TANK_CD_MINUTES
from data.models_avenger import get_avenger, get_avenger_status, mark_avenger_looted, reset_avenger
from data.models_egg import get_egg, get_egg_status, mark_egg_looted, reset_egg
from data.models_heli import get_heli, get_heli_status, mark_heli_looted, reset_heli, HELI_CD_MINUTES
from data.models_patrol import get_patrol, get_patrol_status, mark_patrol_looted, reset_patrol, PATROL_CD_MINUTES
from data.models_cargo import get_cargo, get_cargo_status, mark_cargo_looted, reset_cargo, CARGO_CD_MINUTES
from data.models_medal import get_medal, get_medal_status, mark_medal_looted, reset_medal
from states.states_loot import LootSettings
from data.models_clan import get_user_clan, get_clan_server_id
from data.models_clan_loot import save_clan_loot_event
from data.models_wipe import get_active_server
from data.models_clan_rooms import (
    get_clan_all_slots, get_clan_slot, set_clan_card_type,
    mark_clan_looted, reset_clan_slot_timer,
    get_clan_room_cd, set_clan_room_cd,
    get_clan_slot_looted_by,
)


async def _save_clan_loot(user_id: int, event_name: str, cd_minutes: int):
    clan = await get_user_clan(user_id)
    if not clan:
        return
    srv_id = await get_clan_server_id(clan["id"])
    if not srv_id:
        return
    await save_clan_loot_event(clan["id"], user_id, event_name, cd_minutes)


async def _can_see_settings(user_id: int) -> bool:
    clan = await get_user_clan(user_id)
    if not clan:
        return True
    return clan["role"] == "owner"


async def _get_clan_context(user_id: int) -> tuple[int | None, bool]:
    clan = await get_user_clan(user_id)
    if not clan:
        return None, False
    return clan["id"], clan["role"] == "owner"


async def _slots(user_id: int, clan_id: int | None) -> dict:
    if clan_id:
        return await get_clan_all_slots(clan_id)
    return await get_all_slots(user_id)


async def _slot(user_id: int, clan_id: int | None, location: str, slot: int) -> dict | None:
    if clan_id:
        return await get_clan_slot(clan_id, location, slot)
    return await get_slot(user_id, location, slot)


async def _cd(user_id: int, clan_id: int | None) -> dict:
    if clan_id:
        return await get_clan_room_cd(clan_id)
    return await get_user_cd_minutes(user_id)


async def _get_event_secs(user_id: int, clan_id: int | None,
                          event: str, personal_fn) -> float:
    if clan_id:
        row = await get_clan_slot(clan_id, event, 0)
        return row["seconds_left"] if row else 0.0
    return await personal_fn(user_id)


async def _mark_event(user_id: int, clan_id: int | None,
                      event: str, mode: str, cd: int, personal_fn):
    if clan_id:
        await mark_clan_looted(
            clan_id, event, 0,
            notify_mode=mode,
            looted_by=user_id,
            minutes_override=cd,
            card_type_override=event,
        )
    else:
        await personal_fn(user_id, notify_mode=mode, cd_minutes=cd)


async def _reset_event(user_id: int, clan_id: int | None,
                       event: str, personal_fn):
    if clan_id:
        await reset_clan_slot_timer(clan_id, event, 0)
    else:
        await personal_fn(user_id)


router = Router()

_LOOT_BASE = (
    "🎮 <b>Здесь ты можешь отметить, что именно залутал.</b>\n"
    "\n"
    "Бот автоматически поставит таймер и напомнит, когда лут снова будет доступен.\n"
)

_LOOT_ITEMS = [
    ('<tg-emoji emoji-id="5325863428198265230">🚗</tg-emoji> Танк',    get_tank_status,    "tank"),
    ('<tg-emoji emoji-id="5341780894824831113">😈</tg-emoji> Мститель', get_avenger_status, "avenger"),
    ('<tg-emoji emoji-id="5341313306030283326">🥚</tg-emoji> Монст Егг',get_egg_status,     "egg"),
    ('<tg-emoji emoji-id="5323546495205536651">🚁</tg-emoji> Вертолет', get_heli_status,    "heli"),
    ('<tg-emoji emoji-id="5386642223368530459">🪂</tg-emoji> Десант',   get_patrol_status,  "patrol"),
    ('<tg-emoji emoji-id="5323526957399308323">🚢</tg-emoji> Карго',    get_cargo_status,   "cargo"),
    ('<tg-emoji emoji-id="5305349315772839031">🏅</tg-emoji> Медаль',   get_medal_status,   "medal"),
]


async def _build_loot_text(user_id: int) -> str:
    clan_id, _ = await _get_clan_context(user_id)
    timer_lines = []
    for label, fn, event_key in _LOOT_ITEMS:
        if clan_id:
            row = await get_clan_slot(clan_id, event_key, 0)
            status = row["seconds_left"] if row else None
        else:
            status = await fn(user_id)
        if status is None:
            continue
        if status > 0:
            timer_lines.append(f"{label} — ⏳ {format_time_left(status)}")

    all_slots = await _slots(user_id, clan_id)
    room_lines = []
    for loc_key, loc in LOCATIONS.items():
        slot_parts = []
        for slot_idx in range(loc["slots"]):
            slot_data = all_slots.get((loc_key, slot_idx))
            if not slot_data or not slot_data.get("looted_at"):
                continue
            card = slot_data.get("card_type") or ""
            seconds = slot_data.get("seconds_left", 0.0)
            if seconds > 0:
                emoji = CARD_EMOJI_HTML.get(card, "")
                slot_parts.append(f"К{slot_idx + 1} {emoji} ⏳ {format_time_left(seconds)}")
        if slot_parts:
            room_lines.append(f"{loc['emoji']} {loc['name']} — " + " | ".join(slot_parts))

    text = _LOOT_BASE
    if timer_lines:
        text += "\n" + "\n".join(timer_lines) + "\n"
    if room_lines:
        text += "\n🏠 <b>Комнаты:</b>\n" + "\n".join(room_lines) + "\n"
    text += "\nВыбери событие ниже 👇"
    return text

ROOMS_TEXT = (
    '<tg-emoji emoji-id="5305359387471149323">🔵</tg-emoji> <b>Комнаты (чипы)</b> <tg-emoji emoji-id="5307762520457507728">🟣</tg-emoji>\n'
    "\n"
    "<blockquote>Выбери локацию. Отметь какой чип ты залутал "
    "— бот запустит таймер и напомнит когда чип снова заспавнится.</blockquote>\n"
    "\n"
    "⚪ — не настроено   ⏳ — кулдаун"
)


def _slot_text(loc_key: str, slot: int, card_type: str | None, seconds_left: float, cd_minutes: dict | None = None) -> str:
    loc = LOCATIONS[loc_key]
    header = f"{loc['emoji']} <b>{loc['name']}</b> — Комната {slot + 1}"
    if not card_type:
        return f"{header}\n\n❓ Карта не указана\n\nВыбери какая карта заспавнилась:"
    cd_min = (cd_minutes or DEFAULT_MINUTES)[card_type]
    emoji = CARD_EMOJI_HTML[card_type]
    name = CARD_NAMES[card_type]
    if seconds_left > 0:
        return (
            f"{header}\n\n"
            f"{emoji} <b>{name} карта</b>\n"
            f"⏳ Кулдаун: {format_minutes(cd_min)}\n"
            f"🕐 Доступна через: <b>{format_time_left(seconds_left)}</b>"
        )
    return (
        f"{header}\n\n"
        f"{emoji} <b>{name} карта</b>\n"
        f"⏳ Кулдаун: {format_minutes(cd_min)}\n"
        f"✅ <b>Доступна — можно лутать!</b>"
    )


def _cd_text(cd_minutes: dict[str, int]) -> str:
    return (
        "⚙️ <b>Настройка времени спауна карт</b>\n\n"
        "<blockquote>Укажи своё время спауна для каждой карты.\n"
        "Применяется ко всем локациям.</blockquote>\n\n"
        f'{CARD_EMOJI_HTML["blue"]} Синяя:      <b>{format_minutes(cd_minutes["blue"])}</b>\n'
        f"🟣 Фиолетовая: <b>{format_minutes(cd_minutes['purple'])}</b>"
    )


_NOTIFY_CHOICE_TEXT = (
    "✅ Залутал!\n\n"
    "🔔 Хочешь получить уведомление когда снова будет доступно?"
)


@router.callback_query(F.data == "loot")
async def loot_handler(callback: CallbackQuery):
    active = await get_active_server(callback.from_user.id)
    if not active:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏱ Настроить вайп", callback_data="wipe")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
        ])
        await safe_edit_text(
            callback.message,
            "🎮 <b>Лутание</b>\n\n"
            "Чтобы использовать таймеры лута, сначала добавь свой сервер в разделе <b>Вайп</b>.\n"
            "Бот будет отсчитывать кулдауны и присылать уведомления.",
            reply_markup=kb,
        )
        await callback.answer()
        return
    text = await _build_loot_text(callback.from_user.id)
    await safe_edit_text(callback.message, text, reply_markup=loot_menu())
    await callback.answer()


@router.callback_query(F.data == "rooms")
async def rooms_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    slots_data = await _slots(uid, clan_id)
    await callback.message.edit_text(ROOMS_TEXT, parse_mode="HTML", reply_markup=rooms_list_kb(slots_data))
    await callback.answer()


@router.callback_query(F.data.startswith("room_"))
async def room_location_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    loc_key = callback.data.removeprefix("room_")
    if loc_key not in LOCATIONS:
        await callback.answer("Неизвестная локация", show_alert=True)
        return
    loc = LOCATIONS[loc_key]
    slots_data = await _slots(uid, clan_id)

    if loc["fixed"]:
        for i, card_type in enumerate(loc["fixed"]):
            if (loc_key, i) not in slots_data:
                if clan_id:
                    await set_clan_card_type(clan_id, loc_key, i, card_type)
                else:
                    await set_card_type(uid, loc_key, i, card_type)
        slots_data = await _slots(uid, clan_id)

    ss = await _can_see_settings(uid)
    text = f"{loc['emoji']} <b>{loc['name']}</b>\n\nВыбери чип:"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=location_kb(loc_key, slots_data, ss))
    await callback.answer()


@router.callback_query(F.data.startswith("rslot_"))
async def slot_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    parts = callback.data.split("_")
    slot = int(parts[-1])
    loc_key = "_".join(parts[1:-1])
    if loc_key not in LOCATIONS:
        await callback.answer("Неизвестная локация", show_alert=True)
        return
    loc = LOCATIONS[loc_key]
    is_fixed = bool(loc["fixed"])

    if is_fixed:
        card_type = loc["fixed"][slot]
        row = await _slot(uid, clan_id, loc_key, slot)
        seconds_left = row["seconds_left"] if row else 0.0
    else:
        row = await _slot(uid, clan_id, loc_key, slot)
        card_type = row["card_type"] if row else None
        seconds_left = row["seconds_left"] if row else 0.0

    cd_minutes = await _cd(uid, clan_id)
    text = _slot_text(loc_key, slot, card_type, seconds_left, cd_minutes)
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=slot_kb(loc_key, slot, card_type, seconds_left, is_fixed),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rset_"))
async def set_card_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    parts = callback.data.split("_")
    card_type = parts[-1]
    slot = int(parts[-2])
    loc_key = "_".join(parts[1:-2])
    if loc_key not in LOCATIONS or card_type not in ("blue", "purple"):
        await callback.answer("Ошибка", show_alert=True)
        return

    if clan_id:
        await set_clan_card_type(clan_id, loc_key, slot, card_type)
        row = await get_clan_slot(clan_id, loc_key, slot)
    else:
        await set_card_type(uid, loc_key, slot, card_type)
        row = await get_slot(uid, loc_key, slot)

    seconds_left = row["seconds_left"] if row else 0.0
    cd_minutes = await _cd(uid, clan_id)
    text = _slot_text(loc_key, slot, card_type, seconds_left, cd_minutes)
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=slot_kb(loc_key, slot, card_type, seconds_left, is_fixed=False),
    )
    await callback.answer(f"{CARD_EMOJI[card_type]} {CARD_NAMES[card_type]} карта выбрана")


@router.callback_query(F.data.startswith("rreset_"))
async def reset_slot_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    parts = callback.data.split("_")
    slot = int(parts[-1])
    loc_key = "_".join(parts[1:-1])
    if loc_key not in LOCATIONS:
        await callback.answer("Ошибка", show_alert=True)
        return
    if clan_id:
        await reset_clan_slot_timer(clan_id, loc_key, slot)
        row = await get_clan_slot(clan_id, loc_key, slot)
    else:
        await reset_slot_timer(uid, loc_key, slot)
        row = await get_slot(uid, loc_key, slot)
    card_type = row["card_type"] if row else None
    cd_minutes = await _cd(uid, clan_id)
    text = _slot_text(loc_key, slot, card_type, 0.0, cd_minutes)
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=slot_kb(loc_key, slot, card_type, 0.0, is_fixed=bool(LOCATIONS[loc_key]["fixed"])),
    )
    await callback.answer("🔄 Таймер сброшен")


@router.callback_query(F.data.startswith("rloot_"))
async def loot_slot_handler(callback: CallbackQuery):
    parts = callback.data.split("_")
    slot = int(parts[-1])
    loc_key = "_".join(parts[1:-1])
    if loc_key not in LOCATIONS:
        await callback.answer("Ошибка", show_alert=True)
        return
    await callback.message.edit_text(
        _NOTIFY_CHOICE_TEXT,
        parse_mode="HTML",
        reply_markup=loot_notify_choice_kb(
            confirm_prefix=f"rlootm_{loc_key}_{slot}",
            back_cb=f"rslot_{loc_key}_{slot}",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rlootm_"))
async def loot_slot_mode_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    parts = callback.data.split("_")
    mode = parts[-1]
    slot = int(parts[-2])
    loc_key = "_".join(parts[1:-2])
    if loc_key not in LOCATIONS or mode not in ("once", "none", "twice"):
        await callback.answer("Ошибка", show_alert=True)
        return

    cd_minutes = await _cd(uid, clan_id)
    if clan_id:
        await mark_clan_looted(clan_id, loc_key, slot, notify_mode=mode,
                               cd_minutes=cd_minutes, looted_by=uid)
        row = await get_clan_slot(clan_id, loc_key, slot)
    else:
        await mark_looted(uid, loc_key, slot, notify_mode=mode)
        row = await get_slot(uid, loc_key, slot)

    card_type = row["card_type"]
    seconds_left = row["seconds_left"]
    await _save_clan_loot(uid, "room", int(cd_minutes.get(card_type or "blue", 120)))
    text = _slot_text(loc_key, slot, card_type, seconds_left, cd_minutes)
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=slot_kb(loc_key, slot, card_type, seconds_left, is_fixed=bool(LOCATIONS[loc_key]["fixed"])),
    )
    cd_label = format_minutes(cd_minutes.get(card_type or "blue", 120))
    await callback.answer(f"⏱ Таймер {cd_label} запущен!", show_alert=False)


@router.callback_query(F.data.startswith("rconf_"))
async def location_settings_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    loc_key = callback.data.removeprefix("rconf_")
    if loc_key not in LOCATIONS:
        await callback.answer("Ошибка", show_alert=True)
        return
    loc = LOCATIONS[loc_key]
    text = f"⚙️ <b>Настройка — {loc['emoji']} {loc['name']}</b>\n\nВыбери действие:"
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=location_settings_main_kb(loc_key),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rchangecards_"))
async def change_cards_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    loc_key = callback.data.removeprefix("rchangecards_")
    if loc_key not in LOCATIONS:
        await callback.answer("Ошибка", show_alert=True)
        return
    loc = LOCATIONS[loc_key]
    slots_data = await _slots(uid, clan_id)
    text = f"🔄 <b>Сменить карты — {loc['emoji']} {loc['name']}</b>\n\nВыбери чип:"
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=location_cards_edit_kb(loc_key, slots_data),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("redit_"))
async def slot_edit_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    parts = callback.data.split("_")
    slot = int(parts[-1])
    loc_key = "_".join(parts[1:-1])
    if loc_key not in LOCATIONS:
        await callback.answer("Ошибка", show_alert=True)
        return
    loc = LOCATIONS[loc_key]
    row = await _slot(uid, clan_id, loc_key, slot)
    current_card = row["card_type"] if row else None
    text = (
        f"🔄 <b>{loc['emoji']} {loc['name']}</b> — Комната {slot + 1}\n\n"
        f"Текущая карта: {CARD_EMOJI_HTML[current_card] + ' ' + CARD_NAMES[current_card] if current_card else '❓ не указана'}\n\n"
        f"Выбери новую карту:"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=slot_edit_kb(loc_key, slot, current_card),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rsave_"))
async def slot_save_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    parts = callback.data.split("_")
    card_type = parts[-1]
    slot = int(parts[-2])
    loc_key = "_".join(parts[1:-2])
    if loc_key not in LOCATIONS or card_type not in ("blue", "purple"):
        await callback.answer("Ошибка", show_alert=True)
        return
    if clan_id:
        await set_clan_card_type(clan_id, loc_key, slot, card_type)
        slots_data = await get_clan_all_slots(clan_id)
    else:
        await set_card_type(uid, loc_key, slot, card_type)
        slots_data = await get_all_slots(uid)
    loc = LOCATIONS[loc_key]
    text = f"🔄 <b>Сменить карты — {loc['emoji']} {loc['name']}</b>\n\nВыбери чип:"
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=location_cards_edit_kb(loc_key, slots_data),
    )
    await callback.answer(f"{CARD_EMOJI[card_type]} {CARD_NAMES[card_type]} сохранена")


@router.callback_query(F.data.startswith("rspawn_"))
async def spawn_settings_handler(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    await state.clear()
    loc_key = callback.data.removeprefix("rspawn_")
    if loc_key not in LOCATIONS:
        await callback.answer("Ошибка", show_alert=True)
        return
    cd_minutes = await _cd(uid, clan_id)
    await state.update_data(clan_id=clan_id)
    await callback.message.edit_text(
        _cd_text(cd_minutes),
        parse_mode="HTML",
        reply_markup=location_spawn_kb(loc_key, cd_minutes),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rcdset_"))
async def cd_set_start(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    parts = callback.data.split("_")
    card_type = parts[-1]
    loc_key = "_".join(parts[1:-1])
    if loc_key not in LOCATIONS or card_type not in ("blue", "purple"):
        await callback.answer("Ошибка", show_alert=True)
        return
    await state.set_state(
        LootSettings.set_blue_cd if card_type == "blue" else LootSettings.set_purple_cd
    )
    await state.update_data(loc_key=loc_key, card_type=card_type, clan_id=clan_id)
    emoji = CARD_EMOJI_HTML[card_type]
    name = CARD_NAMES[card_type]
    cd_minutes = await _cd(uid, clan_id)
    current = format_minutes(cd_minutes[card_type])
    clan_note = "\n<i>Изменение применится ко всему клану.</i>" if clan_id else ""
    await callback.message.edit_text(
        f"✏️ <b>{emoji} {name} карта</b>\n\n"
        f"Текущее время: <b>{current}</b>\n\n"
        f"Введи новое время спауна в формате <b>Ч:ММ</b>\n"
        f"<i>Например: 3:10 (3 часа 10 минут)</i>{clan_note}",
        parse_mode="HTML",
        reply_markup=cd_cancel_kb(loc_key),
    )
    await callback.answer()


@router.message(LootSettings.set_blue_cd)
@router.message(LootSettings.set_purple_cd)
async def cd_set_value(message: Message, state: FSMContext):
    uid = message.from_user.id
    data = await state.get_data()
    loc_key   = data["loc_key"]
    card_type = data["card_type"]
    clan_id   = data.get("clan_id")
    minutes = parse_hm(message.text or "")
    if not minutes:
        await message.answer(
            f"❗ Неверный формат. Введи в виде <b>Ч:ММ</b>\n"
            f"<i>Например: 3:10</i>",
            parse_mode="HTML",
            reply_markup=cd_cancel_kb(loc_key),
        )
        return
    if clan_id:
        await set_clan_room_cd(clan_id, card_type, minutes)
        cd_minutes = await get_clan_room_cd(clan_id)
    else:
        await set_user_cd_minutes(uid, card_type, minutes)
        cd_minutes = await get_user_cd_minutes(uid)
    await state.clear()
    emoji = CARD_EMOJI_HTML[card_type]
    name = CARD_NAMES[card_type]
    clan_note = " (для всего клана)" if clan_id else ""
    await message.answer(
        f"✅ {emoji} <b>{name}</b> — время обновлено{clan_note}: <b>{format_minutes(minutes)}</b>",
        parse_mode="HTML",
        reply_markup=location_spawn_kb(loc_key, cd_minutes),
    )


def _tank_text(seconds_left: float) -> str:
    base = (
        '<tg-emoji emoji-id="5325863428198265230">🚗</tg-emoji> <b>Танк</b>\n\n'
        "<blockquote>Танк спавнится в Аэропорту.\n"
        f"Кулдаун: 6 часов.</blockquote>\n\n"
    )
    if seconds_left > 0:
        return base + f"⏳ Кулдаун: 6ч\n🕐 Доступен через: <b>{format_time_left(seconds_left)}</b>"
    return base + "✅ <b>Доступен — можно лутать!</b>"


@router.callback_query(F.data == "loot_tank")
async def loot_tank(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    seconds_left = await _get_event_secs(uid, clan_id, "tank", get_tank)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _tank_text(seconds_left), parse_mode="HTML", reply_markup=tank_kb(seconds_left, ss)
    )
    await callback.answer()


@router.callback_query(F.data == "tank_loot")
async def tank_loot_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        _NOTIFY_CHOICE_TEXT, parse_mode="HTML",
        reply_markup=loot_notify_choice_kb("tank_lootm", "loot_tank"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tank_lootm_"))
async def tank_lootm_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    mode = callback.data.split("_")[-1]
    cd = await get_user_event_cd(uid, "tank")
    await _mark_event(uid, clan_id, "tank", mode, cd, mark_tank_looted)
    await _save_clan_loot(uid, "tank", cd)
    seconds_left = await _get_event_secs(uid, clan_id, "tank", get_tank)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _tank_text(seconds_left), parse_mode="HTML", reply_markup=tank_kb(seconds_left, ss)
    )
    await callback.answer(f"⏱ Таймер {format_minutes(cd)} запущен!")


@router.callback_query(F.data == "tank_reset")
async def tank_reset_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    await _reset_event(uid, clan_id, "tank", reset_tank)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _tank_text(0.0), parse_mode="HTML", reply_markup=tank_kb(0.0, ss)
    )
    await callback.answer("🔄 Таймер сброшен")


def _avenger_text(seconds_left: float) -> str:
    base = (
        '<tg-emoji emoji-id="5341780894824831113">😈</tg-emoji> <b>Мститель</b>\n\n'
        "<blockquote>Мститель спавнится на Милке.\n"
        "Кулдаун: 6 часов.</blockquote>\n\n"
    )
    if seconds_left > 0:
        return base + f"⏳ Кулдаун: 6ч\n🕐 Доступен через: <b>{format_time_left(seconds_left)}</b>"
    return base + "✅ <b>Доступен — можно лутать!</b>"


@router.callback_query(F.data == "loot_avenger")
async def loot_avenger(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    seconds_left = await _get_event_secs(uid, clan_id, "avenger", get_avenger)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _avenger_text(seconds_left), parse_mode="HTML", reply_markup=avenger_kb(seconds_left, ss)
    )
    await callback.answer()


@router.callback_query(F.data == "avenger_loot")
async def avenger_loot_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        _NOTIFY_CHOICE_TEXT, parse_mode="HTML",
        reply_markup=loot_notify_choice_kb("avenger_lootm", "loot_avenger"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("avenger_lootm_"))
async def avenger_lootm_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    mode = callback.data.split("_")[-1]
    cd = await get_user_event_cd(uid, "avenger")
    await _mark_event(uid, clan_id, "avenger", mode, cd, mark_avenger_looted)
    await _save_clan_loot(uid, "avenger", cd)
    seconds_left = await _get_event_secs(uid, clan_id, "avenger", get_avenger)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _avenger_text(seconds_left), parse_mode="HTML", reply_markup=avenger_kb(seconds_left, ss)
    )
    await callback.answer(f"⏱ Таймер {format_minutes(cd)} запущен!")


@router.callback_query(F.data == "avenger_reset")
async def avenger_reset_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    await _reset_event(uid, clan_id, "avenger", reset_avenger)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _avenger_text(0.0), parse_mode="HTML", reply_markup=avenger_kb(0.0, ss)
    )
    await callback.answer("🔄 Таймер сброшен")


def _egg_text(seconds_left: float) -> str:
    base = (
        '<tg-emoji emoji-id="5341313306030283326">🥚</tg-emoji> <b>Монст Егг</b>\n\n'
        "<blockquote>Монст Егг спавнится в Лаборатории.\n"
        "Кулдаун: 6 часов.</blockquote>\n\n"
    )
    if seconds_left > 0:
        return base + f"⏳ Кулдаун: 6ч\n🕐 Доступен через: <b>{format_time_left(seconds_left)}</b>"
    return base + "✅ <b>Доступен — можно лутать!</b>"


@router.callback_query(F.data == "loot_egg")
async def loot_egg(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    seconds_left = await _get_event_secs(uid, clan_id, "egg", get_egg)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _egg_text(seconds_left), parse_mode="HTML", reply_markup=egg_kb(seconds_left, ss)
    )
    await callback.answer()


@router.callback_query(F.data == "egg_loot")
async def egg_loot_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        _NOTIFY_CHOICE_TEXT, parse_mode="HTML",
        reply_markup=loot_notify_choice_kb("egg_lootm", "loot_egg"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("egg_lootm_"))
async def egg_lootm_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    mode = callback.data.split("_")[-1]
    cd = await get_user_event_cd(uid, "egg")
    await _mark_event(uid, clan_id, "egg", mode, cd, mark_egg_looted)
    await _save_clan_loot(uid, "egg", cd)
    seconds_left = await _get_event_secs(uid, clan_id, "egg", get_egg)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _egg_text(seconds_left), parse_mode="HTML", reply_markup=egg_kb(seconds_left, ss)
    )
    await callback.answer(f"⏱ Таймер {format_minutes(cd)} запущен!")


@router.callback_query(F.data == "egg_reset")
async def egg_reset_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    await _reset_event(uid, clan_id, "egg", reset_egg)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _egg_text(0.0), parse_mode="HTML", reply_markup=egg_kb(0.0, ss)
    )
    await callback.answer("🔄 Таймер сброшен")


@router.callback_query(F.data == "loot_bots")
async def loot_bots(callback: CallbackQuery):
    await callback.answer("🤖 Боты возле комнат — скоро будет", show_alert=True)


@router.callback_query(F.data == "loot_drop")
async def loot_drop(callback: CallbackQuery):
    await callback.answer("📦 Дроп — скоро будет", show_alert=True)


def _heli_text(seconds_left: float) -> str:
    base = (
        '<tg-emoji emoji-id="5323546495205536651">🚁</tg-emoji> <b>Вертолет</b>\n\n'
        "<blockquote>Кулдаун: 6ч 15мин.</blockquote>\n\n"
    )
    if seconds_left > 0:
        return base + f"⏳ Кулдаун: 6ч 15мин\n🕐 Доступен через: <b>{format_time_left(seconds_left)}</b>"
    return base + "✅ <b>Доступен — можно лутать!</b>"


@router.callback_query(F.data == "loot_heli")
async def loot_heli(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    seconds_left = await _get_event_secs(uid, clan_id, "heli", get_heli)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _heli_text(seconds_left), parse_mode="HTML", reply_markup=heli_kb(seconds_left, ss)
    )
    await callback.answer()


@router.callback_query(F.data == "heli_loot")
async def heli_loot_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        _NOTIFY_CHOICE_TEXT, parse_mode="HTML",
        reply_markup=loot_notify_choice_kb("heli_lootm", "loot_heli"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("heli_lootm_"))
async def heli_lootm_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    mode = callback.data.split("_")[-1]
    cd = await get_user_event_cd(uid, "heli")
    await _mark_event(uid, clan_id, "heli", mode, cd, mark_heli_looted)
    await _save_clan_loot(uid, "heli", cd)
    seconds_left = await _get_event_secs(uid, clan_id, "heli", get_heli)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _heli_text(seconds_left), parse_mode="HTML", reply_markup=heli_kb(seconds_left, ss)
    )
    await callback.answer(f"⏱ Таймер {format_minutes(cd)} запущен!")


@router.callback_query(F.data == "heli_reset")
async def heli_reset_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    await _reset_event(uid, clan_id, "heli", reset_heli)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _heli_text(0.0), parse_mode="HTML", reply_markup=heli_kb(0.0, ss)
    )
    await callback.answer("🔄 Таймер сброшен")


def _patrol_text(seconds_left: float) -> str:
    base = (
        '<tg-emoji emoji-id="5386642223368530459">🪂</tg-emoji> <b>Десант</b>\n\n'
        "<blockquote>Кулдаун: 6 часов.</blockquote>\n\n"
    )
    if seconds_left > 0:
        return base + f"⏳ Кулдаун: 6ч\n🕐 Доступен через: <b>{format_time_left(seconds_left)}</b>"
    return base + "✅ <b>Доступен — можно лутать!</b>"


@router.callback_query(F.data == "loot_patrol")
async def loot_patrol(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    seconds_left = await _get_event_secs(uid, clan_id, "patrol", get_patrol)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _patrol_text(seconds_left), parse_mode="HTML", reply_markup=patrol_kb(seconds_left, ss)
    )
    await callback.answer()


@router.callback_query(F.data == "patrol_loot")
async def patrol_loot_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        _NOTIFY_CHOICE_TEXT, parse_mode="HTML",
        reply_markup=loot_notify_choice_kb("patrol_lootm", "loot_patrol"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("patrol_lootm_"))
async def patrol_lootm_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    mode = callback.data.split("_")[-1]
    cd = await get_user_event_cd(uid, "patrol")
    await _mark_event(uid, clan_id, "patrol", mode, cd, mark_patrol_looted)
    await _save_clan_loot(uid, "patrol", cd)
    seconds_left = await _get_event_secs(uid, clan_id, "patrol", get_patrol)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _patrol_text(seconds_left), parse_mode="HTML", reply_markup=patrol_kb(seconds_left, ss)
    )
    await callback.answer(f"⏱ Таймер {format_minutes(cd)} запущен!")


@router.callback_query(F.data == "patrol_reset")
async def patrol_reset_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    await _reset_event(uid, clan_id, "patrol", reset_patrol)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _patrol_text(0.0), parse_mode="HTML", reply_markup=patrol_kb(0.0, ss)
    )
    await callback.answer("🔄 Таймер сброшен")


def _cargo_text(seconds_left: float) -> str:
    base = (
        '<tg-emoji emoji-id="5323526957399308323">🚢</tg-emoji> <b>Карго</b>\n\n'
        "<blockquote>Кулдаун: 6ч 30мин.</blockquote>\n\n"
    )
    if seconds_left > 0:
        return base + f"⏳ Кулдаун: 6ч 30мин\n🕐 Доступен через: <b>{format_time_left(seconds_left)}</b>"
    return base + "✅ <b>Доступен — можно лутать!</b>"


@router.callback_query(F.data == "loot_cargo")
async def loot_cargo(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    seconds_left = await _get_event_secs(uid, clan_id, "cargo", get_cargo)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _cargo_text(seconds_left), parse_mode="HTML", reply_markup=cargo_kb(seconds_left, ss)
    )
    await callback.answer()


@router.callback_query(F.data == "cargo_loot")
async def cargo_loot_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        _NOTIFY_CHOICE_TEXT, parse_mode="HTML",
        reply_markup=loot_notify_choice_kb("cargo_lootm", "loot_cargo"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cargo_lootm_"))
async def cargo_lootm_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    mode = callback.data.split("_")[-1]
    cd = await get_user_event_cd(uid, "cargo")
    await _mark_event(uid, clan_id, "cargo", mode, cd, mark_cargo_looted)
    await _save_clan_loot(uid, "cargo", cd)
    seconds_left = await _get_event_secs(uid, clan_id, "cargo", get_cargo)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _cargo_text(seconds_left), parse_mode="HTML", reply_markup=cargo_kb(seconds_left, ss)
    )
    await callback.answer(f"⏱ Таймер {format_minutes(cd)} запущен!")


@router.callback_query(F.data == "cargo_reset")
async def cargo_reset_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    await _reset_event(uid, clan_id, "cargo", reset_cargo)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _cargo_text(0.0), parse_mode="HTML", reply_markup=cargo_kb(0.0, ss)
    )
    await callback.answer("🔄 Таймер сброшен")


@router.callback_query(F.data == "loot_miniboss")
async def loot_miniboss(callback: CallbackQuery):
    uid = callback.from_user.id
    rooms_data = await get_all_miniboss(uid)
    await callback.message.edit_text(
        '<tg-emoji emoji-id="5348271844539537866">👾</tg-emoji> <b>Мини-боссы</b>\n\nОтметь локацию когда залутал — бот напомнит через 30 мин.',
        parse_mode="HTML",
        reply_markup=miniboss_kb(rooms_data),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mb_loot_"))
async def mb_loot_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    loc_key = callback.data[len("mb_loot_"):]
    if loc_key not in MINIBOSS_ROOMS:
        await callback.answer("Неизвестная локация")
        return
    await mark_miniboss_looted(uid, loc_key)
    rooms_data = await get_all_miniboss(uid)
    await callback.message.edit_reply_markup(reply_markup=miniboss_kb(rooms_data))
    loc = MINIBOSS_ROOMS[loc_key]
    await callback.answer(f"⏱ {loc['name']} — таймер 30 мин запущен!")


@router.callback_query(F.data.startswith("mb_reset_"))
async def mb_reset_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    loc_key = callback.data[len("mb_reset_"):]
    if loc_key not in MINIBOSS_ROOMS:
        await callback.answer("Неизвестная локация")
        return
    await reset_miniboss(uid, loc_key)
    rooms_data = await get_all_miniboss(uid)
    await callback.message.edit_reply_markup(reply_markup=miniboss_kb(rooms_data))
    loc = MINIBOSS_ROOMS[loc_key]
    await callback.answer(f"🔄 {loc['name']} — таймер сброшен")


def _medal_text(seconds_left: float, cd_minutes: int) -> str:
    cd_label = format_minutes(cd_minutes)
    base = (
        '<tg-emoji emoji-id="5305349315772839031">🏅</tg-emoji> <b>Медаль</b>\n\n'
        f"<blockquote>Кулдаун: {cd_label}.</blockquote>\n\n"
    )
    if seconds_left > 0:
        return base + f"⏳ Кулдаун: {cd_label}\n🕐 Доступна через: <b>{format_time_left(seconds_left)}</b>"
    return base + "✅ <b>Доступна — можно лутать!</b>"


@router.callback_query(F.data == "loot_medal")
async def loot_medal(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    seconds_left = await _get_event_secs(uid, clan_id, "medal", get_medal)
    cd = await get_user_event_cd(uid, "medal")
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _medal_text(seconds_left, cd), parse_mode="HTML", reply_markup=medal_kb(seconds_left, ss)
    )
    await callback.answer()


@router.callback_query(F.data == "medal_loot")
async def medal_loot_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        _NOTIFY_CHOICE_TEXT, parse_mode="HTML",
        reply_markup=loot_notify_choice_kb("medal_lootm", "loot_medal"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("medal_lootm_"))
async def medal_lootm_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    mode = callback.data.split("_")[-1]
    cd = await get_user_event_cd(uid, "medal")
    await _mark_event(uid, clan_id, "medal", mode, cd, mark_medal_looted)
    await _save_clan_loot(uid, "medal", cd)
    seconds_left = await _get_event_secs(uid, clan_id, "medal", get_medal)
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _medal_text(seconds_left, cd), parse_mode="HTML", reply_markup=medal_kb(seconds_left, ss)
    )
    await callback.answer(f"⏱ Таймер {format_minutes(cd)} запущен!")


@router.callback_query(F.data == "medal_reset")
async def medal_reset_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    await _reset_event(uid, clan_id, "medal", reset_medal)
    cd = await get_user_event_cd(uid, "medal")
    ss = await _can_see_settings(uid)
    await callback.message.edit_text(
        _medal_text(0.0, cd), parse_mode="HTML", reply_markup=medal_kb(0.0, ss)
    )
    await callback.answer("🔄 Таймер сброшен")


_EVENT_BACK: dict[str, str] = {
    "tank":    "loot_tank",
    "avenger": "loot_avenger",
    "egg":     "loot_egg",
    "heli":    "loot_heli",
    "patrol":  "loot_patrol",
    "cargo":   "loot_cargo",
    "medal":   "loot_medal",
}


@router.callback_query(F.data.startswith("nloot_"))
async def notify_quick_loot_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    clan_id, _ = await _get_clan_context(uid)
    parts = callback.data.split("_")
    slot = int(parts[-1])
    loc_key = "_".join(parts[1:-1])
    if loc_key not in LOCATIONS:
        await callback.answer("Ошибка", show_alert=True)
        return

    if clan_id:
        already = await get_clan_slot_looted_by(clan_id, loc_key, slot)
        if already and already.get("looted_by") and already["looted_by"] != uid:
            name = already.get("first_name") or already.get("username") or "Игрок"
            time_left = format_time_left(already["seconds_left"])
            loc = LOCATIONS[loc_key]
            await callback.answer(
                f"{loc['emoji']} Комната {slot + 1}\n"
                f"✅ {name} уже залутал!\n"
                f"⏳ Доступно через: {time_left}",
                show_alert=True,
            )
            return
        row = await get_clan_slot(clan_id, loc_key, slot)
        notify_mode = row["notify_mode"] if row else "once"
        cd_minutes = await get_clan_room_cd(clan_id)
        await mark_clan_looted(clan_id, loc_key, slot, notify_mode=notify_mode,
                               cd_minutes=cd_minutes, looted_by=uid)
        row = await get_clan_slot(clan_id, loc_key, slot)
        card_type = row["card_type"] if row else None
        seconds_left = row["seconds_left"] if row else 0.0
        text = _slot_text(loc_key, slot, card_type, seconds_left, cd_minutes)
        await callback.message.edit_text(text, parse_mode="HTML")
        await callback.answer("⏱ Таймер запущен!")
    else:
        row = await get_slot(uid, loc_key, slot)
        notify_mode = row["notify_mode"] if row else "once"
        await mark_looted(uid, loc_key, slot, notify_mode=notify_mode)
        row = await get_slot(uid, loc_key, slot)
        cd_minutes = await get_user_cd_minutes(uid)
        card_type = row["card_type"] if row else None
        seconds_left = row["seconds_left"] if row else 0.0
        text = _slot_text(loc_key, slot, card_type, seconds_left, cd_minutes)
        await callback.message.edit_text(text, parse_mode="HTML")
        await callback.answer("⏱ Таймер запущен!")


@router.callback_query(F.data.startswith("evset_"))
async def event_settings_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    event = callback.data.removeprefix("evset_")
    if event not in LOOT_ITEM_LABELS:
        await callback.answer("Ошибка", show_alert=True)
        return
    emoji, name = LOOT_ITEM_LABELS[event]
    cd = await get_user_event_cd(callback.from_user.id, event)
    default = EVENT_DEFAULTS[event]
    text = (
        f"⚙️ <b>Настройка — {emoji} {name}</b>\n\n"
        f"Кулдаун: <b>{format_minutes(cd)}</b>"
        + (f" <i>(по умолчанию: {format_minutes(default)})</i>" if cd != default else "")
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=event_settings_kb(event, _EVENT_BACK[event]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("evcdset_"))
async def event_cd_set_start(callback: CallbackQuery, state: FSMContext):
    event = callback.data.removeprefix("evcdset_")
    if event not in LOOT_ITEM_LABELS:
        await callback.answer("Ошибка", show_alert=True)
        return
    emoji, name = LOOT_ITEM_LABELS[event]
    cd = await get_user_event_cd(callback.from_user.id, event)
    await state.set_state(LootSettings.set_event_cd)
    await state.update_data(event=event)
    await callback.message.edit_text(
        f"✏️ <b>{emoji} {name}</b>\n\n"
        f"Текущий кулдаун: <b>{format_minutes(cd)}</b>\n\n"
        f"Введи новое время в формате <b>Ч:ММ</b>\n"
        f"<i>Например: 6:00</i>",
        parse_mode="HTML",
        reply_markup=event_cd_cancel_kb(event),
    )
    await callback.answer()


@router.message(LootSettings.set_event_cd)
async def event_cd_set_value(message: Message, state: FSMContext):
    data = await state.get_data()
    event = data["event"]
    minutes = parse_hm(message.text or "")
    if not minutes:
        await message.answer(
            "❗ Неверный формат. Введи в виде <b>Ч:ММ</b>\n<i>Например: 6:00</i>",
            parse_mode="HTML",
            reply_markup=event_cd_cancel_kb(event),
        )
        return
    await set_user_event_cd(message.from_user.id, event, minutes)
    await state.clear()
    emoji, name = LOOT_ITEM_LABELS[event]
    await message.answer(
        f"✅ {emoji} <b>{name}</b> — кулдаун обновлён: <b>{format_minutes(minutes)}</b>",
        parse_mode="HTML",
        reply_markup=event_settings_kb(event, _EVENT_BACK[event]),
    )
