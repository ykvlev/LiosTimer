import asyncio
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

RATE_PER_SECOND = 20


@dataclass
class QueuedMessage:
    user_id: int
    text: str
    parse_mode: str = "HTML"
    kwargs: dict = field(default_factory=dict)


class MessageQueue:
    def __init__(self):
        self._queue: asyncio.Queue[QueuedMessage] = asyncio.Queue()
        self._bot = None

    def setup(self, bot):
        self._bot = bot

    async def send(self, user_id: int, text: str, parse_mode: str = "HTML", **kwargs):
        await self._queue.put(QueuedMessage(user_id, text, parse_mode, kwargs))

    async def run(self):
        while True:
            start = asyncio.get_event_loop().time()
            sent = 0
            while sent < RATE_PER_SECOND:
                try:
                    msg = self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                try:
                    await self._bot.send_message(
                        msg.user_id, msg.text, parse_mode=msg.parse_mode, **msg.kwargs
                    )
                except Exception as e:
                    logger.warning("mq send error user_id=%s: %s", msg.user_id, e)
                sent += 1
            elapsed = asyncio.get_event_loop().time() - start
            await asyncio.sleep(max(0.0, 1.0 - elapsed))


mq = MessageQueue()
