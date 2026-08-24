from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.keyboards.notifications_menu import notifications_kb
from bot.utils.nav import safe_edit_text
from data.models_notifications import get_notif_settings, toggle_notif, NOTIF_KEYS

router = Router()

_TEXT = (
    "🔔 <b>Уведомления</b>\n"
    "\n"
    "Выбери, какие уведомления ты хочешь получать.\n"
    "Нажми на кнопку чтобы включить или выключить:"
)


@router.callback_query(F.data == "notifications")
async def notifications_handler(callback: CallbackQuery):
    await callback.answer()
    settings = await get_notif_settings(callback.from_user.id)
    await safe_edit_text(callback.message, _TEXT, reply_markup=notifications_kb(settings))


@router.callback_query(F.data.startswith("notif_toggle:"))
async def notif_toggle_handler(callback: CallbackQuery):
    key = callback.data.split(":")[1]
    if key not in NOTIF_KEYS:
        await callback.answer()
        return
    new_val = await toggle_notif(callback.from_user.id, key)
    label = NOTIF_KEYS[key]
    state = "включены" if new_val else "выключены"
    await callback.answer(f"{label} — {state}", show_alert=False)
    settings = await get_notif_settings(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=notifications_kb(settings))
