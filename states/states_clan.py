from aiogram.fsm.state import State, StatesGroup


class ClanCreate(StatesGroup):
    waiting_name = State()
    waiting_tag = State()


class ClanJoin(StatesGroup):
    waiting_tag = State()


class ClanServerAdd(StatesGroup):
    wipe_type = State()
    name = State()
    hours = State()
    pending_hours = State()


class ClanSettings(StatesGroup):
    waiting_photo = State()
    waiting_new_name = State()
    waiting_new_tag  = State()
