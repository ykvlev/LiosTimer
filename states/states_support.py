from aiogram.fsm.state import State, StatesGroup


class SupportChat(StatesGroup):
    chatting = State()


class SupportReply(StatesGroup):
    waiting_text = State()
