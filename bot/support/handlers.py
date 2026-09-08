import html
import logging

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.support.keyboards import (
    support_intro_kb,
    support_chat_kb,
    admin_ticket_notify_kb,
    admin_tickets_kb,
    admin_ticket_kb,
    admin_reply_cancel_kb,
)
from bot.utils.nav import safe_edit_text
from config.settings import load_config
from data.models_support import (
    get_open_ticket,
    get_ticket,
    open_ticket,
    close_ticket,
    add_message,
    get_messages,
    get_tickets_page,
    get_tickets_pages_count,
)
from data.models_users import get_admin_ids, get_user_is_admin
from states.states_support import SupportChat, SupportReply

logger = logging.getLogger(__name__)
router = Router()
config = load_config()

MAX_MESSAGE_LEN = 2000

INTRO_TEXT = (
    "🛠 <b>Связь с разработчиками</b>\n\n"
    "Напиши свой вопрос или опиши проблему — сообщение попадёт разработчикам.\n"
    "Ответ придёт сюда же, прямо в бот.\n\n"
    "<i>Диалог анонимный: ты не увидишь, кто именно отвечает.</i>"
)


async def _is_admin(user_id: int) -> bool:
    return user_id == config.admin_id or await get_user_is_admin(user_id)


async def _admin_ids() -> list[int]:
    ids = set(await get_admin_ids())
    if config.admin_id:
        ids.add(config.admin_id)
    return list(ids)


async def _notify_admins(bot: Bot, ticket_id: int, text: str):
    body = (
        f"📩 <b>Новое сообщение — обращение #{ticket_id}</b>\n\n"
        f"{html.escape(text)}"
    )
    for admin_id in await _admin_ids():
        try:
            await bot.send_message(
                admin_id, body, parse_mode="HTML",
                reply_markup=admin_ticket_notify_kb(ticket_id),
            )
        except Exception as e:
            logger.warning("support notify error admin_id=%s: %s", admin_id, e)


# ─── КОРИСТУВАЦЬКА ЧАСТИНА ───────────────────────────────────────────────────

@router.callback_query(F.data == "support")
async def support_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    ticket = await get_open_ticket(callback.from_user.id)
    await safe_edit_text(callback.message, INTRO_TEXT, reply_markup=support_intro_kb(bool(ticket)))
    await callback.answer()


@router.callback_query(F.data == "support_write")
async def support_write(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SupportChat.chatting)
    await safe_edit_text(
        callback.message,
        "✍️ <b>Напиши сообщение</b>\n\nОтправь текст — он уйдёт разработчикам.",
        reply_markup=support_chat_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "support_close")
async def support_close(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    ticket = await get_open_ticket(callback.from_user.id)
    if ticket:
        await close_ticket(ticket["id"])
    await safe_edit_text(
        callback.message,
        "✅ Диалог с разработчиками завершён.\n\nЕсли что-то ещё — пиши в любой момент.",
        reply_markup=support_intro_kb(has_open_ticket=False),
    )
    await callback.answer()


@router.message(SupportChat.chatting, F.text)
async def support_user_message(message: Message):
    text = message.text.strip()
    if len(text) > MAX_MESSAGE_LEN:
        await message.answer(
            f"❗ Слишком длинное сообщение (максимум {MAX_MESSAGE_LEN} символов).",
            reply_markup=support_chat_kb(),
        )
        return
    ticket = await open_ticket(message.from_user.id)
    await add_message(ticket["id"], "user", text)
    await _notify_admins(message.bot, ticket["id"], text)
    await message.answer(
        "✅ Сообщение отправлено разработчикам.\nОтвет придёт сюда.",
        reply_markup=support_chat_kb(),
    )


@router.message(SupportChat.chatting)
async def support_user_wrong(message: Message):
    await message.answer("❗ Отправь текстовое сообщение.", reply_markup=support_chat_kb())


# ─── АДМІНСЬКА ЧАСТИНА ───────────────────────────────────────────────────────

async def _ticket_text(ticket: dict) -> str:
    messages = await get_messages(ticket["id"])
    lines = [
        f"📨 <b>Обращение #{ticket['id']}</b>",
        f"Пользователь: <code>{ticket['user_id']}</code>",
        f"Статус: {'🟢 открыто' if ticket['status'] == 'open' else '⚪️ закрыто'}",
        "",
    ]
    if not messages:
        lines.append("Сообщений пока нет.")
    for m in messages:
        who = "👤 Пользователь" if m["sender"] == "user" else "🛠 Ответ"
        lines.append(f"{who}: {html.escape(m['text'])}")
    return "\n".join(lines)


@router.callback_query(F.data.startswith("admin_tickets_"))
async def admin_tickets(callback: CallbackQuery, state: FSMContext):
    if not await _is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.clear()
    page = int(callback.data.split("_")[-1])
    tickets = await get_tickets_page(page)
    total_pages = await get_tickets_pages_count()
    text = (
        f"✉️ <b>Обращения</b> (стр. {page}/{total_pages})\n\n"
        + ("Открытых обращений нет." if not tickets else "Выбери обращение чтобы ответить.")
    )
    await safe_edit_text(callback.message, text, reply_markup=admin_tickets_kb(tickets, page, total_pages))
    await callback.answer()


@router.callback_query(F.data.startswith("sup_ticket_"))
async def admin_ticket_view(callback: CallbackQuery, state: FSMContext):
    if not await _is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.clear()
    parts = callback.data.split("_")
    ticket_id, page = int(parts[2]), int(parts[3])
    ticket = await get_ticket(ticket_id)
    if not ticket:
        await callback.answer("Обращение не найдено", show_alert=True)
        return
    await safe_edit_text(
        callback.message,
        await _ticket_text(ticket),
        reply_markup=admin_ticket_kb(ticket_id, page, is_open=ticket["status"] == "open"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sup_reply_"))
async def admin_reply_start(callback: CallbackQuery, state: FSMContext):
    if not await _is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    ticket_id = int(callback.data.split("_")[2])
    ticket = await get_ticket(ticket_id)
    if not ticket:
        await callback.answer("Обращение не найдено", show_alert=True)
        return
    await state.set_state(SupportReply.waiting_text)
    await state.update_data(ticket_id=ticket_id)
    await callback.message.answer(
        f"💬 <b>Ответ на обращение #{ticket_id}</b>\n\n"
        "Введи текст — пользователь получит его от имени бота, без твоего имени.",
        parse_mode="HTML",
        reply_markup=admin_reply_cancel_kb(ticket_id),
    )
    await callback.answer()


@router.message(SupportReply.waiting_text, F.text)
async def admin_reply_send(message: Message, state: FSMContext):
    if not await _is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    ticket = await get_ticket(data["ticket_id"])
    if not ticket:
        await state.clear()
        await message.answer("❗ Обращение не найдено.")
        return
    text = message.text.strip()
    await add_message(ticket["id"], "admin", text, admin_id=message.from_user.id)
    await state.clear()
    try:
        await message.bot.send_message(
            ticket["user_id"],
            f"🛠 <b>Ответ разработчиков</b>\n\n{html.escape(text)}",
            parse_mode="HTML",
            reply_markup=support_chat_kb(),
        )
    except Exception as e:
        logger.warning("support reply send error user_id=%s: %s", ticket["user_id"], e)
        await message.answer("❗ Не удалось доставить ответ пользователю.")
        return
    await message.answer(
        f"✅ Ответ отправлен по обращению #{ticket['id']}.",
        reply_markup=admin_ticket_kb(ticket["id"], 1, is_open=ticket["status"] == "open"),
    )


@router.message(SupportReply.waiting_text)
async def admin_reply_wrong(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer("❗ Введи текст ответа.", reply_markup=admin_reply_cancel_kb(data["ticket_id"]))


@router.callback_query(F.data.startswith("sup_close_"))
async def admin_ticket_close(callback: CallbackQuery, state: FSMContext):
    if not await _is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await state.clear()
    ticket_id = int(callback.data.split("_")[2])
    ticket = await get_ticket(ticket_id)
    if not ticket:
        await callback.answer("Обращение не найдено", show_alert=True)
        return
    await close_ticket(ticket_id)
    try:
        await callback.bot.send_message(
            ticket["user_id"],
            "✅ <b>Обращение закрыто разработчиками.</b>\n\nЕсли вопрос остался — напиши снова.",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("support close notify error user_id=%s: %s", ticket["user_id"], e)
    ticket["status"] = "closed"
    await safe_edit_text(
        callback.message,
        await _ticket_text(ticket),
        reply_markup=admin_ticket_kb(ticket_id, 1, is_open=False),
    )
    await callback.answer("✅ Обращение закрыто")
