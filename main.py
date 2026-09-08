import asyncio
import logging

from aiogram import Bot, Dispatcher

from config.settings import load_config
from bot.handlers import register_all
from data.database import init_db
from bot.wipe.scheduler import wipe_scheduler
from bot.loot.scheduler import loot_scheduler
from bot.prize.scheduler import prize_scheduler
from bot.utils.message_queue import mq

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def main():
    await init_db()
    config = load_config()
    bot = Bot(token=config.bot_token)
    mq.setup(bot)
    dp = Dispatcher()
    register_all(dp)
    asyncio.create_task(mq.run())
    asyncio.create_task(wipe_scheduler())
    asyncio.create_task(loot_scheduler())
    asyncio.create_task(prize_scheduler())
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user interrupt")
