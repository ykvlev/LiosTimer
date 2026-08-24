from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.wipe.keyboards_main import wipe_main_kb
from bot.utils.nav import safe_edit_text
from data.models_wipe import get_active_server

router = Router()

WIPE_TEXT = (
    "🧹 <b>Вайп</b>\n"
    "\n"
    "<blockquote>"
    "Добавь свой сервер и скажи боту, когда был последний вайп — "
    "он сам будет считать время до следующего и напоминать о луте, событиях и рейдах."
    "</blockquote>"
)


@router.callback_query(F.data == "wipe")
async def wipe_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    active = await get_active_server(callback.from_user.id)
    await safe_edit_text(callback.message, WIPE_TEXT, reply_markup=wipe_main_kb(active))
    await callback.answer()
