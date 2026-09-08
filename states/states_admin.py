from aiogram.fsm.state import State, StatesGroup


class AdminSearch(StatesGroup):
    waiting_query = State()


class AdminMenuPhoto(StatesGroup):
    waiting_photo = State()


class AdminGrantByUsername(StatesGroup):
    waiting_username = State()


class AdminGrantModByUsername(StatesGroup):
    waiting_username = State()
