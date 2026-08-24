from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.models_prize import (
    get_prize_servers, get_prize_server, add_prize_server,
    update_prize_server, delete_prize_server,
    entities_to_json, json_to_entities,
)
from bot.admin.handlers_main import is_admin

router = Router()


class PrizeServerForm(StatesGroup):
    # Add flow (sequential)
    add_title = State()
    add_prize_pool = State()
    add_photos = State()
    add_post_text = State()
    # Edit individual fields
    edit_title = State()
    edit_prize_pool = State()
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
            text=f"⚙️ {s['title']}",
            callback_data=f"admin_prize_edit_{s['id']}",
        ))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel"))
    return b.as_markup()


def prize_edit_kb(server_id: int):
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✏️ Название", callback_data=f"admin_prize_field_title_{server_id}"),
        InlineKeyboardButton(text="💰 Призовой пул", callback_data=f"admin_prize_field_prize_{server_id}"),
    )
    b.row(
        InlineKeyboardButton(text="🖼 Фото", callback_data=f"admin_prize_field_photos_{server_id}"),
        InlineKeyboardButton(text="📝 Текст поста", callback_data=f"admin_prize_field_text_{server_id}"),
    )
    b.row(InlineKeyboardButton(text="🎨 Эмодзи кнопки", callback_data=f"admin_prize_field_emoji_{server_id}"))
    b.row(InlineKeyboardButton(text="👁 Предпросмотр", callback_data=f"admin_prize_preview_{server_id}"))
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

def _summary(data: dict) -> str:
    photos_count = len(data.get("photos") or [])
    return (
        "📋 <b>Данные сервера:</b>\n\n"
        f"📛 <b>Название:</b> {data.get('title') or '—'}\n"
        f"💰 <b>Призовой пул:</b> {data.get('prize_pool') or '—'}\n"
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
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.clear()
    servers = await get_prize_servers()
    text = "🏆 <b>Призовые сервера</b>" + ("\n\nСписок пуст." if not servers else "")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=prize_list_kb(servers))
    await callback.answer()


# ── ADD flow ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_prize_add")
async def prize_add_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.clear()
    await state.set_state(PrizeServerForm.add_title)
    await callback.message.edit_text(
        "🏆 <b>Новый призовой сервер</b>\n\n<b>Шаг 1/4.</b> Введи <b>название</b> сервера:",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(PrizeServerForm.add_title)
async def add_title_msg(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(PrizeServerForm.add_prize_pool)
    await message.answer(
        "<b>Шаг 2/4.</b> Введи <b>призовой пул</b> (например: <code>20$+10$</code>)\n\n"
        "Или <b>—</b> чтобы пропустить.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(PrizeServerForm.add_prize_pool)
async def add_prize_pool_msg(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(prize_pool=None if text == "—" else text, photos=[])
    await state.set_state(PrizeServerForm.add_photos)
    await message.answer(
        "<b>Шаг 3/4.</b> Отправь <b>фото</b> (до 3 штук).\n\nКнопка «Пропустить» — если фото не нужно.",
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
        "<b>Шаг 4/4.</b> Отправь <b>текст поста</b>.\n\n"
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
    )
    if editing_id:
        await update_prize_server(editing_id, **fields)
        msg = f"✅ Сервер <b>{fields['title']}</b> обновлён!"
    else:
        await add_prize_server(**fields)
        msg = f"✅ Сервер <b>{fields['title']}</b> добавлен!"
    await state.clear()
    servers = await get_prize_servers()
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
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.clear()
    server_id = int(callback.data.split("_")[-1])
    s = await get_prize_server(server_id)
    if not s:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    photos_count = sum(1 for k in ("photo1", "photo2", "photo3") if s.get(k))
    text = (
        f"⚙️ <b>{s['title']}</b>\n\n"
        f"💰 Пул: {s.get('prize_pool') or '—'}\n"
        f"🖼 Фото: {photos_count} шт.\n"
        f"📝 Текст: {'✅ есть' if s.get('post_text') else '—'}"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=prize_edit_kb(server_id))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_prize_preview_"))
async def admin_prize_preview(callback: CallbackQuery, bot: Bot):
    if not await is_admin(callback.from_user.id):
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
    if not await is_admin(callback.from_user.id):
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
    if not await is_admin(callback.from_user.id):
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


@router.callback_query(F.data.startswith("admin_prize_field_photos_"))
async def edit_field_photos(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
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
    if not await is_admin(callback.from_user.id):
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
    if not await is_admin(callback.from_user.id):
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


# ── Delete ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_prize_del_"))
async def admin_prize_delete(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    server_id = int(callback.data.split("_")[-1])
    await delete_prize_server(server_id)
    await state.clear()
    servers = await get_prize_servers()
    text = "🏆 <b>Призовые сервера</b>\n\nСервер удалён." + ("\n\nСписок пуст." if not servers else "")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=prize_list_kb(servers))
    await callback.answer("Удалено")
