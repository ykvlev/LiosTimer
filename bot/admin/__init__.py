from aiogram import Router

from .handlers_main import router as main_router
from .handlers_users import router as users_router
from .handlers_prize import router as prize_router

router = Router()
router.include_router(main_router)
router.include_router(users_router)
router.include_router(prize_router)
