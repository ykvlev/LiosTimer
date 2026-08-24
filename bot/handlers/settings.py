from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.keyboards.settings_menu import settings_kb
from bot.utils.nav import safe_edit_text

router = Router()

_SETTINGS_TEXT = "⚙️ <b>Настройки</b>\n\nВыбери действие:"


@router.callback_query(F.data == "settings")
async def settings_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit_text(callback.message, _SETTINGS_TEXT, reply_markup=settings_kb())
    await callback.answer()
