from aiogram.fsm.state import State, StatesGroup


class AddServer(StatesGroup):
    name = State()
    wipe_type = State()
    hours = State()
    pending_hours = State()


class EditServer(StatesGroup):
    hours = State()


class QuickStart(StatesGroup):
    name = State()
    hours = State()


class ClanAddServer(StatesGroup):
    wipe_type     = State()
    name          = State()
    hours         = State()
    pending_hours = State()


class ClanQuickStart(StatesGroup):
    name  = State()
    hours = State()
