from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config.settings import load_config
from data.models_users import get_user_is_banned

BAN_TEXT = "🚫 Вы заблокированы администрацией. Доступ к боту закрыт."
_OWNER_ID = load_config().admin_id

# user_id, которым уже показали сообщение о бане (одно на сессию бота).
_notified: set[int] = set()


class BanMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        if user is None or user.id == _OWNER_ID:
            return await handler(event, data)

        if not await get_user_is_banned(user.id):
            _notified.discard(user.id)
            return await handler(event, data)

        # Забаннен — гасим апдейт, один раз сообщаем причину.
        if isinstance(event, CallbackQuery):
            await event.answer(BAN_TEXT, show_alert=True)
        elif isinstance(event, Message) and user.id not in _notified:
            _notified.add(user.id)
            try:
                await event.answer(BAN_TEXT)
            except Exception:
                pass
        return None
