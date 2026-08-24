from aiogram import Dispatcher

from . import start, loot, notifications, clan, clan_wipe, settings
from bot.admin import router as admin_router
from bot.wipe import router as wipe_router
from bot.prize import router as prize_router
from bot.subscription import router as subscription_router


def register_all(dp: Dispatcher):
    for module in [start, loot, notifications, clan, clan_wipe, settings]:
        dp.include_router(module.router)
    dp.include_router(wipe_router)
    dp.include_router(prize_router)
    dp.include_router(subscription_router)
    dp.include_router(admin_router)
