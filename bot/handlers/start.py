from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from bot.keyboards.main_menu import main_menu
from config.settings import load_config
from data.models_users import save_user, get_user_is_admin, get_user_is_moderator, get_total_users
from data.models_wipe import get_active_server
from data.models_settings import get_global_photo
from data.models_clan import get_user_clan, get_clan_server_id, get_clan_photo
from data.models_wipe import get_server, format_countdown

router = Router()
config = load_config()

async def _welcome_text() -> str:
    count = await get_total_users()
    return (
        "🎮 <b>Lios Timer Bot</b> — поможет не пропускать лут и важные события.\n"
        f"👥 Игроков: <b>{count}</b>"
    )


async def _clan_server_label(clan: dict | None) -> str | None:
    if not clan:
        return None
    srv_id = await get_clan_server_id(clan["id"])
    if not srv_id:
        return None
    srv = await get_server(srv_id)
    if not srv:
        return None
    return f"Вайп клана {srv['name']} — {format_countdown(srv['hours_left'])}"


async def _get_menu_photo(clan: dict | None) -> str | None:
    if clan:
        clan_photo = await get_clan_photo(clan["id"])
        if clan_photo:
            return clan_photo
    return await get_global_photo()


async def _send_main_menu(target, user_id: int, is_admin: bool):
    active = await get_active_server(user_id)
    clan = await get_user_clan(user_id)
    clan_name = clan["name"] if clan else None
    clan_srv = await _clan_server_label(clan)
    is_mod = (not is_admin) and await get_user_is_moderator(user_id)
    kb = main_menu(is_admin=is_admin, active_server=active, clan_name=clan_name,
                   clan_server_label=clan_srv, is_moderator=is_mod)
    photo = await _get_menu_photo(clan)
    text = await _welcome_text()
    if photo:
        await target.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await save_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    is_admin = message.from_user.id == config.admin_id or await get_user_is_admin(message.from_user.id)
    await _send_main_menu(message, message.from_user.id, is_admin)


@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    is_admin = callback.from_user.id == config.admin_id or await get_user_is_admin(callback.from_user.id)
    active = await get_active_server(callback.from_user.id)
    clan = await get_user_clan(callback.from_user.id)
    clan_name = clan["name"] if clan else None
    clan_srv = await _clan_server_label(clan)
    is_mod = (not is_admin) and await get_user_is_moderator(callback.from_user.id)
    kb = main_menu(is_admin=is_admin, active_server=active, clan_name=clan_name,
                   clan_server_label=clan_srv, is_moderator=is_mod)
    photo = await _get_menu_photo(clan)
    text = await _welcome_text()
    try:
        await callback.message.delete()
    except Exception:
        pass
    if photo:
        await callback.message.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()
