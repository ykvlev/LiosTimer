from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.models_prize import (
    get_prize_servers_admin, get_prize_server, add_prize_server,
    update_prize_server, delete_prize_server, set_prize_pinned, is_expired,
    entities_to_json, json_to_entities,
    parse_launch_input, format_launch,
)
from data.models_users import get_user_is_admin, get_user_is_moderator
from config.settings import load_config

router = Router()
_config = load_config()


async def is_prize_editor(user_id: int) -> bool:
    """Призовые сервера могут вести админы и модераторы."""
    if user_id == _config.admin_id:
        return True
    return await get_user_is_admin(user_id) or await get_user_is_moderator(user_id)


class PrizeServerForm(StatesGroup):
    # Add flow (sequential)
    add_title = State()
    add_prize_pool = State()
    add_launch = State()
    add_wipe_days = State()
    add_photos = State()
    add_post_text = State()
    # Edit individual fields
    edit_title = State()
    edit_prize_pool = State()
    edit_launch = State()
    edit_wipe_days = State()
    edit_photos = State()
    edit_post_text = State()
    edit_button_emoji = State()
    # Shared confirm
    confirm = State()


# ── Keyboards ─────────────────────────────────────────────────────────────────

def prize_list_kb(servers: list[dict]):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="➕ Добавить сервер", callback_data="admin_prize_add"))
    for s in servers:
        b.row(InlineKeyboardButton(
            text=_list_label(s),
            callback_data=f"admin_prize_edit_{s['id']}",
        ))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel"))
    return b.as_markup()


def _list_label(s: dict) -> str:
    if is_expired(s):
        mark = "🏁"
    elif s.get("pinned"):
        mark = "📌"
    else:
        mark = "⚙️"
    label = f"{mark} {s['title']}"
    short = format_launch(s.get("launch_at")).replace(" МСК", "")
    if short != "—":
        label += f" · {short}"
    return label


def prize_edit_kb(s: dict):
    server_id = s["id"]
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✏️ Название", callback_data=f"admin_prize_field_title_{server_id}"),
        InlineKeyboardButton(text="💰 Призовой пул", callback_data=f"admin_prize_field_prize_{server_id}"),
    )
    b.row(
        InlineKeyboardButton(text="📅 Дата выхода", callback_data=f"admin_prize_field_launch_{server_id}"),
        InlineKeyboardButton(text="📆 Дней вайпа", callback_data=f"admin_prize_field_days_{server_id}"),
    )
    b.row(
        InlineKeyboardButton(text="🖼 Фото", callback_data=f"admin_prize_field_photos_{server_id}"),
        InlineKeyboardButton(text="📝 Текст поста", callback_data=f"admin_prize_field_text_{server_id}"),
    )
    b.row(InlineKeyboardButton(text="🎨 Эмодзи кнопки", callback_data=f"admin_prize_field_emoji_{server_id}"))
    b.row(InlineKeyboardButton(text="👁 Предпросмотр", callback_data=f"admin_prize_preview_{server_id}"))
    if s.get("pinned"):
        b.row(InlineKeyboardButton(text="📌 Открепить", callback_data=f"admin_prize_unpin_{server_id}"))
    else:
        b.row(InlineKeyboardButton(text="📌 Закрепить вверху", callback_data=f"admin_prize_pin_{server_id}"))
    b.row(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_prize_del_{server_id}"))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_prize"))
    return b.as_markup()


def photos_kb(count: int, back: str = "admin_prize"):
    b = InlineKeyboardBuilder()
    if count > 0:
        b.row(InlineKeyboardButton(text=f"✅ Готово ({count}/3)", callback_data="prize_photos_done"))
    else:
        b.row(InlineKeyboardButton(text="⏭ Пропустить", callback_data="prize_photos_done"))
    b.row(InlineKeyboardButton(text="❌ Отмена", callback_data=back))
    return b.as_markup()


def confirm_kb(editing_id: int | None = None):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="✅ Сохранить", callback_data="prize_confirm_save"))
    b.row(
        InlineKeyboardButton(text="✏️ Название", callback_data="prize_confirm_edit_title"),
        InlineKeyboardButton(text="💰 Пул", callback_data="prize_confirm_edit_prize"),
    )
    b.row(
        InlineKeyboardButton(text="📅 Выход", callback_data="prize_confirm_edit_launch"),
        InlineKeyboardButton(text="📆 Дни", callback_data="prize_confirm_edit_days"),
    )
    b.row(
        InlineKeyboardButton(text="🖼 Фото", callback_data="prize_confirm_edit_photos"),
        InlineKeyboardButton(text="📝 Текст", callback_data="prize_confirm_edit_text"),
    )
    back = f"admin_prize_edit_{editing_id}" if editing_id else "admin_prize"
    b.row(InlineKeyboardButton(text="❌ Отмена", callback_data=back))
    return b.as_markup()


def cancel_kb(back: str = "admin_prize"):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="❌ Отмена", callback_data=back))
    return b.as_markup()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_wipe_days(text: str | None):
    """'7' | '7d' | '7д' | '7 дней' -> int (1..60) | None (пропуск) | False (ошибка)."""
    t = (text or "").strip().lower()
    if t == "—":
        return None
    for suf in ("дней", "дня", "день", "d", "д"):
        if t.endswith(suf):
            t = t[: -len(suf)].strip()
            break
    if not t.isdigit():
        return False
    n = int(t)
    return n if 1 <= n <= 60 else False


def _summary(data: dict) -> str:
    photos_count = len(data.get("photos") or [])
    days = data.get("wipe_days")
    return (
        "📋 <b>Данные сервера:</b>\n\n"
        f"📛 <b>Название:</b> {data.get('title') or '—'}\n"
        f"💰 <b>Призовой пул:</b> {data.get('prize_pool') or '—'}\n"
        f"📅 <b>Выход:</b> {format_launch(data.get('launch_at'))}\n"
        f"📆 <b>Длительность вайпа:</b> {str(days) + ' дн.' if days else '—'}\n"
        f"🖼 <b>Фото:</b> {photos_count} шт.\n"
        f"📝 <b>Текст поста:</b> {'✅ есть' if data.get('post_text') else '—'}"
    )


async def _show_confirm(target, state: FSMContext):
    await state.set_state(PrizeServerForm.confirm)
    data = await state.get_data()
    text = _summary(data)
    kb = confirm_kb(data.get("editing_id"))
    if isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await target.answer()


async def _load_server_to_state(state: FSMContext, server_id: int) -> bool:
    s = await get_prize_server(server_id)
    if not s:
        return False
    photos = [s[k] for k in ("photo1", "photo2", "photo3") if s.get(k)]
    await state.set_data({
        "editing_id": server_id,
        "title": s["title"],
        "prize_pool": s.get("prize_pool"),
        "launch_at": s.get("launch_at"),
        "wipe_days": s.get("wipe_days"),
        "photos": photos,
        "post_text": s.get("post_text"),
        "post_entities": s.get("post_entities"),
        "button_emoji": s.get("button_emoji"),
    })
    return True


async def _send_post(bot: Bot, chat_id: int, photos: list, text: str | None, entities):
    if len(photos) == 1:
        await bot.send_photo(chat_id, photos[0], caption=text, caption_entities=entities)
    elif len(photos) > 1:
        media = [InputMediaPhoto(media=p) for p in photos]
        await bot.send_media_group(chat_id, media)
        if text:
            await bot.send_message(chat_id, text, entities=entities)
    elif text:
        await bot.send_message(chat_id, text, entities=entities)


# ── Main list ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_prize")
async def admin_prize_main(callback: CallbackQuery, state: FSMContext):
    if not await is_prize_editor(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.clear()
    servers = await get_prize_servers_admin()
    text = "🏆 <b>Призовые сервера</b>" + ("\n\nСписок пуст." if not servers else "")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=prize_list_kb(servers))
    await callback.answer()


# ── ADD flow ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_prize_add")
async def prize_add_start(callback: CallbackQuery, state: FSMContext):
    if not await is_prize_editor(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.clear()
    await state.set_state(PrizeServerForm.add_title)
    await callback.message.edit_text(
        "🏆 <b>Новый призовой сервер</b>\n\n<b>Шаг 1/6.</b> Введи <b>название</b> сервера:",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(PrizeServerForm.add_title)
async def add_title_msg(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(PrizeServerForm.add_prize_pool)
    await message.answer(
        "<b>Шаг 2/6.</b> Введи <b>призовой пул</b> (например: <code>20$+10$</code>)\n\n"
        "Или <b>—</b> чтобы пропустить.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(PrizeServerForm.add_prize_pool)
async def add_prize_pool_msg(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(prize_pool=None if text == "—" else text, photos=[])
    await state.set_state(PrizeServerForm.add_launch)
    await message.answer(
        "<b>Шаг 3/6.</b> Введи <b>дату и время выхода</b> сервера (МСК):\n"
        "<i>Например: 08.09 18:00</i>\n\n"
        "Или <b>—</b> чтобы пропустить (тогда без авто-сортировки и авто-удаления).",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(PrizeServerForm.add_launch)
async def add_launch_msg(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "—":
        await state.update_data(launch_at=None, wipe_days=None)
        await state.set_state(PrizeServerForm.add_photos)
        await message.answer(
            "<b>Шаг 5/6.</b> Отправь <b>фото</b> (до 3 штук).\n\nКнопка «Пропустить» — если фото не нужно.",
            parse_mode="HTML",
            reply_markup=photos_kb(0),
        )
        return
    try:
        launch_at = parse_launch_input(text)
    except ValueError as e:
        await message.answer(f"❗ {e}\n<i>Например: 08.09 18:00</i>", parse_mode="HTML", reply_markup=cancel_kb())
        return
    await state.update_data(launch_at=launch_at)
    await state.set_state(PrizeServerForm.add_wipe_days)
    await message.answer(
        "<b>Шаг 4/6.</b> Сколько <b>дней длится вайп</b>? (число, 1–60)\n"
        "Когда вайп закончится — сервер сам пропадёт из списка.\n\n"
        "Или <b>—</b> чтобы не удалять автоматически.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(PrizeServerForm.add_wipe_days)
async def add_wipe_days_msg(message: Message, state: FSMContext):
    days = _parse_wipe_days(message.text)
    if days is False:
        await message.answer("❗ Введи число от 1 до 60, или — чтобы пропустить.", reply_markup=cancel_kb())
        return
    await state.update_data(wipe_days=days, photos=[])
    await state.set_state(PrizeServerForm.add_photos)
    await message.answer(
        "<b>Шаг 5/6.</b> Отправь <b>фото</b> (до 3 штук).\n\nКнопка «Пропустить» — если фото не нужно.",
        parse_mode="HTML",
        reply_markup=photos_kb(0),
    )


@router.message(PrizeServerForm.add_post_text)
async def add_post_text_msg(message: Message, state: FSMContext):
    text = message.text or message.caption
    entities = message.entities or message.caption_entities
    if text and text.strip() == "—":
        await state.update_data(post_text=None, post_entities=None)
    else:
        await state.update_data(post_text=text, post_entities=entities_to_json(entities))
    await _show_confirm(message, state)


# ── EDIT flow (individual fields) ──────────────────────────────────────────────

@router.message(PrizeServerForm.edit_title)
async def edit_title_msg(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await _show_confirm(message, state)


@router.message(PrizeServerForm.edit_prize_pool)
async def edit_prize_pool_msg(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(prize_pool=None if text == "—" else text)
    await _show_confirm(message, state)


@router.message(PrizeServerForm.edit_launch)
async def edit_launch_msg(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "—":
        await state.update_data(launch_at=None)
        await _show_confirm(message, state)
        return
    try:
        await state.update_data(launch_at=parse_launch_input(text))
    except ValueError as e:
        await message.answer(f"❗ {e}\n<i>Например: 08.09 18:00</i>", parse_mode="HTML")
        return
    await _show_confirm(message, state)


@router.message(PrizeServerForm.edit_wipe_days)
async def edit_wipe_days_msg(message: Message, state: FSMContext):
    days = _parse_wipe_days(message.text)
    if days is False:
        await message.answer("❗ Введи число от 1 до 60, или — чтобы убрать.")
        return
    await state.update_data(wipe_days=days)
    await _show_confirm(message, state)


@router.message(PrizeServerForm.edit_post_text)
async def edit_post_text_msg(message: Message, state: FSMContext):
    text = message.text or message.caption
    entities = message.entities or message.caption_entities
    if text and text.strip() == "—":
        await state.update_data(post_text=None, post_entities=None)
    else:
        await state.update_data(post_text=text, post_entities=entities_to_json(entities))
    await _show_confirm(message, state)


# ── Photos (shared for add and edit) ──────────────────────────────────────────

@router.message(
    StateFilter(PrizeServerForm.add_photos, PrizeServerForm.edit_photos),
    F.photo,
)
async def prize_photos_msg(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = list(data.get("photos") or [])
    editing_id = data.get("editing_id")
    back = f"admin_prize_edit_{editing_id}" if editing_id else "admin_prize"
    if len(photos) >= 3:
        await message.answer("Максимум 3 фото уже добавлено.", reply_markup=photos_kb(3, back))
        return
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    if len(photos) == 3:
        await message.answer("Добавлено 3/3 фото. Максимум достигнут.", reply_markup=photos_kb(3, back))
    else:
        await message.answer(f"Фото {len(photos)}/3 добавлено.", reply_markup=photos_kb(len(photos), back))


@router.callback_query(
    StateFilter(PrizeServerForm.add_photos, PrizeServerForm.edit_photos),
    F.data == "prize_photos_done",
)
async def prize_photos_done(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == PrizeServerForm.edit_photos:
        await _show_confirm(callback, state)
        return
    await state.set_state(PrizeServerForm.add_post_text)
    await callback.message.edit_text(
        "<b>Шаг 6/6.</b> Отправь <b>текст поста</b>.\n\n"
        "Используй форматирование Telegram: жирный, курсив, цитаты, премиум-эмодзи — "
        "бот автоматически сохранит всё форматирование и ID эмодзи.\n\n"
        "Или <b>—</b> чтобы пропустить.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


# ── Confirm ───────────────────────────────────────────────────────────────────

@router.callback_query(PrizeServerForm.confirm, F.data == "prize_confirm_save")
async def prize_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = list(data.get("photos") or [])
    editing_id = data.get("editing_id")
    fields = dict(
        title=data.get("title", ""),
        prize_pool=data.get("prize_pool"),
        photo1=photos[0] if len(photos) > 0 else None,
        photo2=photos[1] if len(photos) > 1 else None,
        photo3=photos[2] if len(photos) > 2 else None,
        post_text=data.get("post_text"),
        post_entities=data.get("post_entities"),
        button_emoji=data.get("button_emoji"),
        launch_at=data.get("launch_at"),
        wipe_days=data.get("wipe_days"),
    )
    if editing_id:
        await update_prize_server(editing_id, **fields)
        msg = f"✅ Сервер <b>{fields['title']}</b> обновлён!"
    else:
        await add_prize_server(**fields)
        msg = f"✅ Сервер <b>{fields['title']}</b> добавлен!"
    await state.clear()
    servers = await get_prize_servers_admin()
    suffix = "\n\nСписок пуст." if not servers else ""
    await callback.message.edit_text(
        f"{msg}\n\n🏆 <b>Призовые сервера:</b>{suffix}",
        parse_mode="HTML",
        reply_markup=prize_list_kb(servers),
    )
    await callback.answer()


@router.callback_query(PrizeServerForm.confirm, F.data == "prize_confirm_edit_title")
async def confirm_back_title(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    editing_id = data.get("editing_id")
    back = f"admin_prize_edit_{editing_id}" if editing_id else "admin_prize"
    new_state = PrizeServerForm.edit_title if editing_id else PrizeServerForm.add_title
    await state.set_state(new_state)
    await callback.message.edit_text("✏️ Введи новое <b>название</b> сервера:", parse_mode="HTML", reply_markup=cancel_kb(back))
    await callback.answer()


@router.callback_query(PrizeServerForm.confirm, F.data == "prize_confirm_edit_prize")
async def confirm_back_prize(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    editing_id = data.get("editing_id")
    back = f"admin_prize_edit_{editing_id}" if editing_id else "admin_prize"
    new_state = PrizeServerForm.edit_prize_pool if editing_id else PrizeServerForm.add_prize_pool
    await state.set_state(new_state)
    await callback.message.edit_text("💰 Введи новый <b>призовой пул</b> (или — убрать):", parse_mode="HTML", reply_markup=cancel_kb(back))
    await callback.answer()


@router.callback_query(PrizeServerForm.confirm, F.data == "prize_confirm_edit_launch")
async def confirm_back_launch(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    editing_id = data.get("editing_id")
    back = f"admin_prize_edit_{editing_id}" if editing_id else "admin_prize"
    await state.set_state(PrizeServerForm.edit_launch if editing_id else PrizeServerForm.add_launch)
    await callback.message.edit_text(
        "📅 Введи <b>дату и время выхода</b> (МСК), напр. <code>08.09 18:00</code>\n\nИли <b>—</b> чтобы убрать.",
        parse_mode="HTML", reply_markup=cancel_kb(back),
    )
    await callback.answer()


@router.callback_query(PrizeServerForm.confirm, F.data == "prize_confirm_edit_days")
async def confirm_back_days(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    editing_id = data.get("editing_id")
    back = f"admin_prize_edit_{editing_id}" if editing_id else "admin_prize"
    await state.set_state(PrizeServerForm.edit_wipe_days if editing_id else PrizeServerForm.add_wipe_days)
    await callback.message.edit_text(
        "📆 Сколько <b>дней длится вайп</b>? (1–60)\n\nИли <b>—</b> чтобы убрать авто-удаление.",
        parse_mode="HTML", reply_markup=cancel_kb(back),
    )
    await callback.answer()


@router.callback_query(PrizeServerForm.confirm, F.data == "prize_confirm_edit_photos")
async def confirm_back_photos(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    editing_id = data.get("editing_id")
    back = f"admin_prize_edit_{editing_id}" if editing_id else "admin_prize"
    new_state = PrizeServerForm.edit_photos if editing_id else PrizeServerForm.add_photos
    await state.update_data(photos=[])
    await state.set_state(new_state)
    await callback.message.edit_text("🖼 Отправь новые фото (до 3 штук):", parse_mode="HTML", reply_markup=photos_kb(0, back))
    await callback.answer()


@router.callback_query(PrizeServerForm.confirm, F.data == "prize_confirm_edit_text")
async def confirm_back_text(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    editing_id = data.get("editing_id")
    back = f"admin_prize_edit_{editing_id}" if editing_id else "admin_prize"
    new_state = PrizeServerForm.edit_post_text if editing_id else PrizeServerForm.add_post_text
    await state.set_state(new_state)
    await callback.message.edit_text(
        "📝 Отправь новый <b>текст поста</b> с форматированием.\n\nИли <b>—</b> чтобы убрать.",
        parse_mode="HTML",
        reply_markup=cancel_kb(back),
    )
    await callback.answer()


# ── Edit existing: open menu ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_prize_edit_"))
async def admin_prize_edit_menu(callback: CallbackQuery, state: FSMContext):
    if not await is_prize_editor(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.clear()
    server_id = int(callback.data.split("_")[-1])
    s = await get_prize_server(server_id)
    if not s:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await callback.message.edit_text(_edit_menu_text(s), parse_mode="HTML", reply_markup=prize_edit_kb(s))
    await callback.answer()


def _edit_menu_text(s: dict) -> str:
    photos_count = sum(1 for k in ("photo1", "photo2", "photo3") if s.get(k))
    days = s.get("wipe_days")
    return (
        f"{'📌' if s.get('pinned') else '⚙️'} <b>{s['title']}</b>\n\n"
        f"💰 Пул: {s.get('prize_pool') or '—'}\n"
        f"📅 Выход: {format_launch(s.get('launch_at'))}\n"
        f"📆 Длительность вайпа: {str(days) + ' дн.' if days else '—'}\n"
        f"🖼 Фото: {photos_count} шт.\n"
        f"📝 Текст: {'✅ есть' if s.get('post_text') else '—'}\n"
        f"📌 Закреплён: {'да' if s.get('pinned') else 'нет'}"
        + ("\n\n🏁 <i>Вайп закончился — запись скоро удалится.</i>" if is_expired(s) else "")
    )


async def _rerender_edit_menu(callback: CallbackQuery, server_id: int):
    s = await get_prize_server(server_id)
    if not s:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await callback.message.edit_text(_edit_menu_text(s), parse_mode="HTML", reply_markup=prize_edit_kb(s))


@router.callback_query(F.data.startswith("admin_prize_preview_"))
async def admin_prize_preview(callback: CallbackQuery, bot: Bot):
    if not await is_prize_editor(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    server_id = int(callback.data.split("_")[-1])
    s = await get_prize_server(server_id)
    if not s:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    photos = [s[k] for k in ("photo1", "photo2", "photo3") if s.get(k)]
    entities = json_to_entities(s.get("post_entities"))
    await _send_post(bot, callback.message.chat.id, photos, s.get("post_text"), entities)
    await callback.answer("Предпросмотр отправлен ↑")


# ── Edit existing: field entry points ─────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_prize_field_title_"))
async def edit_field_title(callback: CallbackQuery, state: FSMContext):
    if not await is_prize_editor(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    server_id = int(callback.data.split("_")[-1])
    if not await _load_server_to_state(state, server_id):
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await state.set_state(PrizeServerForm.edit_title)
    await callback.message.edit_text(
        "✏️ Введи новое <b>название</b> сервера:",
        parse_mode="HTML",
        reply_markup=cancel_kb(f"admin_prize_edit_{server_id}"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_prize_field_prize_"))
async def edit_field_prize(callback: CallbackQuery, state: FSMContext):
    if not await is_prize_editor(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    server_id = int(callback.data.split("_")[-1])
    if not await _load_server_to_state(state, server_id):
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await state.set_state(PrizeServerForm.edit_prize_pool)
    await callback.message.edit_text(
        "💰 Введи новый <b>призовой пул</b> (или <b>—</b> чтобы убрать):",
        parse_mode="HTML",
        reply_markup=cancel_kb(f"admin_prize_edit_{server_id}"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_prize_field_launch_"))
async def edit_field_launch(callback: CallbackQuery, state: FSMContext):
    if not await is_prize_editor(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    server_id = int(callback.data.split("_")[-1])
    if not await _load_server_to_state(state, server_id):
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await state.set_state(PrizeServerForm.edit_launch)
    await callback.message.edit_text(
        "📅 Введи <b>дату и время выхода</b> (МСК), напр. <code>08.09 18:00</code>\n\nИли <b>—</b> чтобы убрать.",
        parse_mode="HTML",
        reply_markup=cancel_kb(f"admin_prize_edit_{server_id}"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_prize_field_days_"))
async def edit_field_days(callback: CallbackQuery, state: FSMContext):
    if not await is_prize_editor(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    server_id = int(callback.data.split("_")[-1])
    if not await _load_server_to_state(state, server_id):
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await state.set_state(PrizeServerForm.edit_wipe_days)
    await callback.message.edit_text(
        "📆 Сколько <b>дней длится вайп</b>? (напр. <code>7</code> или <code>7d</code>)\n"
        "По окончании бот сам удалит запись.\n\nИли <b>—</b> чтобы убрать авто-удаление.",
        parse_mode="HTML",
        reply_markup=cancel_kb(f"admin_prize_edit_{server_id}"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_prize_field_photos_"))
async def edit_field_photos(callback: CallbackQuery, state: FSMContext):
    if not await is_prize_editor(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    server_id = int(callback.data.split("_")[-1])
    if not await _load_server_to_state(state, server_id):
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await state.update_data(photos=[])
    await state.set_state(PrizeServerForm.edit_photos)
    await callback.message.edit_text(
        "🖼 Отправь новые <b>фото</b> (до 3 штук). Старые будут заменены.",
        parse_mode="HTML",
        reply_markup=photos_kb(0, back=f"admin_prize_edit_{server_id}"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_prize_field_text_"))
async def edit_field_text(callback: CallbackQuery, state: FSMContext):
    if not await is_prize_editor(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    server_id = int(callback.data.split("_")[-1])
    if not await _load_server_to_state(state, server_id):
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await state.set_state(PrizeServerForm.edit_post_text)
    await callback.message.edit_text(
        "📝 Отправь новый <b>текст поста</b> с форматированием и эмодзи.\n\nИли <b>—</b> чтобы убрать текст.",
        parse_mode="HTML",
        reply_markup=cancel_kb(f"admin_prize_edit_{server_id}"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_prize_field_emoji_"))
async def edit_field_emoji(callback: CallbackQuery, state: FSMContext):
    if not await is_prize_editor(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    server_id = int(callback.data.split("_")[-1])
    if not await _load_server_to_state(state, server_id):
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await state.set_state(PrizeServerForm.edit_button_emoji)
    await callback.message.edit_text(
        "🎨 Отправь сообщение с <b>одним премиум-эмодзи</b> — он будет использован как иконка кнопки сервера.\n\n"
        "Или <b>—</b> чтобы убрать эмодзи.",
        parse_mode="HTML",
        reply_markup=cancel_kb(f"admin_prize_edit_{server_id}"),
    )
    await callback.answer()


@router.message(PrizeServerForm.edit_button_emoji)
async def edit_button_emoji_msg(message: Message, state: FSMContext):
    if message.text and message.text.strip() == "—":
        await state.update_data(button_emoji=None)
        await _show_confirm(message, state)
        return
    entities = message.entities or []
    emoji_id = next(
        (e.custom_emoji_id for e in entities if e.type == "custom_emoji"),
        None,
    )
    if not emoji_id:
        data = await state.get_data()
        back = f"admin_prize_edit_{data.get('editing_id', '')}"
        await message.answer(
            "❌ Премиум-эмодзи не найден. Отправь сообщение с одним премиум-эмодзи.",
            reply_markup=cancel_kb(back),
        )
        return
    await state.update_data(button_emoji=emoji_id)
    await _show_confirm(message, state)


# ── Pin ───────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_prize_pin_"))
async def admin_prize_pin(callback: CallbackQuery):
    if not await is_prize_editor(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    server_id = int(callback.data.split("_")[-1])
    await set_prize_pinned(server_id, True)
    await callback.answer("📌 Закреплён вверху")
    await _rerender_edit_menu(callback, server_id)


@router.callback_query(F.data.startswith("admin_prize_unpin_"))
async def admin_prize_unpin(callback: CallbackQuery):
    if not await is_prize_editor(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    server_id = int(callback.data.split("_")[-1])
    await set_prize_pinned(server_id, False)
    await callback.answer("📌 Откреплён")
    await _rerender_edit_menu(callback, server_id)


# ── Delete ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_prize_del_"))
async def admin_prize_delete(callback: CallbackQuery, state: FSMContext):
    if not await is_prize_editor(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    server_id = int(callback.data.split("_")[-1])
    await delete_prize_server(server_id)
    await state.clear()
    servers = await get_prize_servers_admin()
    text = "🏆 <b>Призовые сервера</b>\n\nСервер удалён." + ("\n\nСписок пуст." if not servers else "")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=prize_list_kb(servers))
    await callback.answer("Удалено")
