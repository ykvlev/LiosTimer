import re

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InputMediaPhoto, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.models_prize import (
    get_prize_servers, get_prize_server, json_to_entities, format_launch_short,
)

router = Router()


def _strip_custom_emoji(text: str) -> str:
    return re.sub(r'[\U00010000-\U0010FFFF]', '', text).strip()


def _list_kb(servers: list[dict]):
    b = InlineKeyboardBuilder()
    for s in servers:
        label = _strip_custom_emoji(s["title"])
        if s.get("pinned"):
            label = f"📌 {label}"
        if s.get("prize_pool"):
            label += f" | {_strip_custom_emoji(s['prize_pool'])}$"
        launch = format_launch_short(s.get("launch_at"))
        if launch:
            label += f" · {launch}"
        btn_kwargs = {"text": label, "callback_data": f"prize_view_{s['id']}"}
        if s.get("button_emoji"):
            btn_kwargs["icon_custom_emoji_id"] = s["button_emoji"]
        b.row(InlineKeyboardButton(**btn_kwargs))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))
    return b.as_markup()


def _back_kb():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="prize_servers"))
    return b.as_markup()


@router.callback_query(F.data == "prize_servers")
async def prize_list(callback: CallbackQuery, bot: Bot):
    servers = await get_prize_servers()
    text = (
        "🏆 <b>Призовые сервера</b>\n\nПока нет активных призовых серверов."
        if not servers
        else "🏆 <b>Призовые сервера</b>\n\nВыбери сервер:"
    )
    await callback.answer()
    if callback.message.text:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_list_kb(servers))
    else:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await bot.send_message(callback.message.chat.id, text, parse_mode="HTML", reply_markup=_list_kb(servers))


@router.callback_query(F.data.startswith("prize_view_"))
async def prize_detail(callback: CallbackQuery, bot: Bot):
    server_id = int(callback.data.split("_")[-1])
    s = await get_prize_server(server_id)
    if not s:
        await callback.answer("Сервер не найден", show_alert=True)
        return

    photos = [s[k] for k in ("photo1", "photo2", "photo3") if s.get(k)]
    text = s.get("post_text")
    entities = json_to_entities(s.get("post_entities"))

    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    if len(photos) == 1:
        await bot.send_photo(
            callback.message.chat.id,
            photos[0],
            caption=text,
            caption_entities=entities,
            reply_markup=_back_kb(),
        )
    elif len(photos) > 1:
        media = [InputMediaPhoto(media=p) for p in photos]
        await bot.send_media_group(callback.message.chat.id, media)
        if text:
            await bot.send_message(
                callback.message.chat.id, text,
                entities=entities, reply_markup=_back_kb(),
            )
        else:
            await bot.send_message(callback.message.chat.id, "—", reply_markup=_back_kb())
    else:
        if text:
            await bot.send_message(
                callback.message.chat.id, text,
                entities=entities, reply_markup=_back_kb(),
            )
        else:
            await bot.send_message(
                callback.message.chat.id,
                "🏆 Нет содержимого.",
                reply_markup=_back_kb(),
            )
