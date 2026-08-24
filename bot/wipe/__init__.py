from aiogram import Router

from .handlers_main import router as main_router
from .handlers_servers import router as servers_router

router = Router()
router.include_router(main_router)
router.include_router(servers_router)
