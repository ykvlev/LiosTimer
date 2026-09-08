from aiogram import Dispatcher

from .ban import BanMiddleware


def setup_middlewares(dp: Dispatcher):
    dp.message.outer_middleware(BanMiddleware())
    dp.callback_query.outer_middleware(BanMiddleware())
