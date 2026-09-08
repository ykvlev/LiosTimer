import asyncio
import logging

from data.models_prize import delete_expired_prize_servers

logger = logging.getLogger(__name__)


async def prize_scheduler():
    while True:
        await asyncio.sleep(300)
        try:
            n = await delete_expired_prize_servers()
            if n:
                logger.info("prize_scheduler: удалено завершённых серверов: %s", n)
        except Exception as e:
            logger.error("Ошибка в prize_scheduler: %s", e)
