from aiogram.fsm.state import State, StatesGroup


class LootSettings(StatesGroup):
    set_blue_cd = State()
    set_purple_cd = State()
    set_event_cd = State()
