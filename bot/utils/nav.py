from aiogram.types import Message, InlineKeyboardMarkup


async def safe_edit_text(
    message: Message,
    text: str,
    parse_mode: str = "HTML",
    reply_markup: InlineKeyboardMarkup | None = None,
):
    if message.photo or message.video or message.document:
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)
    else:
        await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
