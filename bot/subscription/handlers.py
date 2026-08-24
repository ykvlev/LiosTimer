from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, LabeledPrice, PreCheckoutQuery

from bot.subscription.keyboards import (
    sub_plans_kb, sub_payment_kb, sub_ton_check_kb, sub_back_kb,
    presub_plans_kb, presub_payment_kb, presub_ton_check_kb, presub_after_pay_kb,
)
from bot.utils.nav import safe_edit_text
from data.models_clan import get_user_clan
from data.models_subscription import (
    PLAN_NAMES, PLAN_PRICES_USDT, PLAN_PRICES_STARS, PLAN_LIMITS,
    get_clan_subscription, activate_subscription,
    create_ton_order, get_ton_order, get_pending_clan_ton_order,
    mark_ton_order_paid, store_user_sub_credit,
    has_used_trial, mark_trial_used,
)
from bot.subscription.ton_checker import check_ton_payment

router = Router()

TON_WALLET = "UQBrsw7tct-MO8ZkSGsWUZtwH5LImu_Kmjad5kng1mho6RSt"


def _sub_status_text(clan_name: str, sub: dict | None) -> str:
    if not sub:
        return (
            f"💎 <b>Подписка клана {clan_name}</b>\n\n"
            "Текущий план: <b>Нет подписки</b>\n"
            "Без подписки нельзя приглашать участников.\n\n"
            "Выбери план ниже 👇\n"
            "<i>Криптой — скидка 15%!</i>"
        )
    plan = sub["plan"]
    expires = sub["expires_at"][:10]
    limit = PLAN_LIMITS[plan]
    return (
        f"💎 <b>Подписка клана {clan_name}</b>\n\n"
        f"Текущий план: <b>{PLAN_NAMES[plan]}</b>\n"
        f"Участников: до {limit}\n"
        f"Действует до: <b>{expires}</b>\n\n"
        "Купи новый план чтобы продлить или улучшить 👇\n"
        "<i>Криптой — скидка 15%!</i>"
    )


@router.callback_query(F.data == "clan_sub")
async def clan_sub_handler(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        await callback.answer("Нет прав", show_alert=True)
        return
    sub = await get_clan_subscription(clan["id"])
    text = _sub_status_text(clan["name"], sub)
    await safe_edit_text(callback.message, text, reply_markup=sub_plans_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("sub_plan_"))
async def sub_plan_handler(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        await callback.answer("Нет прав", show_alert=True)
        return
    plan = callback.data.split("_")[2]
    if plan not in PLAN_NAMES:
        await callback.answer()
        return
    stars = PLAN_PRICES_STARS[plan]
    usdt = PLAN_PRICES_USDT[plan]
    text = (
        f"💎 <b>{PLAN_NAMES[plan]}</b>\n\n"
        f"⭐ Звёздами: <b>{stars} Stars</b>\n"
        f"💎 TON/USDT: <b>{usdt} USDT</b> <i>(скидка 15%!)</i>\n\n"
        "Выбери способ оплаты 👇"
    )
    await safe_edit_text(callback.message, text, reply_markup=sub_payment_kb(plan))
    await callback.answer()


@router.callback_query(F.data.startswith("sub_stars_"))
async def sub_stars_handler(callback: CallbackQuery, bot: Bot):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        await callback.answer("Нет прав", show_alert=True)
        return
    plan = callback.data.split("_")[2]
    if plan not in PLAN_NAMES:
        await callback.answer()
        return
    stars = PLAN_PRICES_STARS[plan]
    await callback.message.delete()
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Подписка: {PLAN_NAMES[plan]}",
        description=f"30 дней, до {PLAN_LIMITS[plan]} участников в клане.",
        payload=f"clan_sub_{clan['id']}_{plan}",
        currency="XTR",
        prices=[LabeledPrice(label=PLAN_NAMES[plan], amount=stars)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    payload = message.successful_payment.invoice_payload
    parts = payload.split("_")
    if parts[0] == "clan" and parts[1] == "sub" and len(parts) >= 4:
        clan_id = int(parts[2])
        plan = parts[3]
        await activate_subscription(clan_id, plan)
        await message.answer(
            f"✅ <b>Подписка активирована!</b>\n\n"
            f"План: <b>{PLAN_NAMES[plan]}</b>\n"
            "Действует 30 дней. Можешь приглашать участников!",
            parse_mode="HTML",
        )
    elif parts[0] == "clan" and parts[1] == "precreate" and len(parts) >= 3:
        plan = parts[2]
        await store_user_sub_credit(message.from_user.id, plan)
        await message.answer(
            f"✅ <b>Оплата прошла!</b>\n\n"
            f"План: <b>{PLAN_NAMES[plan]}</b>\n"
            "Теперь создай клан — подписка применится автоматически 👇",
            parse_mode="HTML",
            reply_markup=presub_after_pay_kb(),
        )


@router.callback_query(F.data.startswith("sub_ton_") & ~F.data.startswith("sub_ton_check_"))
async def sub_ton_handler(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    if not clan or clan["role"] not in ("owner", "moderator"):
        await callback.answer("Нет прав", show_alert=True)
        return
    plan = callback.data.split("_")[2]
    if plan not in PLAN_NAMES:
        await callback.answer()
        return

    existing = await get_pending_clan_ton_order(clan["id"])
    if existing and existing["plan"] == plan:
        order = existing
    else:
        order = await create_ton_order(clan["id"], callback.from_user.id, plan)

    usdt = order["amount_usdt"]
    memo = order["memo"]
    expires = order["expires_at"][11:16]

    text = (
        f"💎 <b>Оплата через TON</b>\n\n"
        f"План: <b>{PLAN_NAMES[plan]}</b>\n"
        f"Скидка 15% за оплату криптой!\n\n"
        f"1️⃣ Отправь <b>USDT (TON)</b> на кошелёк:\n"
        f"<code>{TON_WALLET}</code>\n\n"
        f"2️⃣ Сумма:\n"
        f"<code>{usdt:.2f}</code> USDT\n\n"
        f"3️⃣ Мемо (обязательно!):\n"
        f"<code>{memo}</code>\n\n"
        f"⏱ Заказ действителен до {expires} UTC\n\n"
        "После оплаты нажми «Проверить» ✅"
    )
    await safe_edit_text(callback.message, text, reply_markup=sub_ton_check_kb(order["id"], plan))
    await callback.answer()


@router.callback_query(F.data == "presub_trial")
async def presub_trial_handler(callback: CallbackQuery):
    if await has_used_trial(callback.from_user.id):
        await callback.answer("Пробный период уже использован", show_alert=True)
        return
    await mark_trial_used(callback.from_user.id)
    await store_user_sub_credit(
        callback.from_user.id, plan="unlimited",
        hours=48, is_trial=True, days=2,
    )
    await safe_edit_text(
        callback.message,
        "🎁 <b>Пробная подписка активирована!</b>\n\n"
        f"План: <b>{PLAN_NAMES['unlimited']}</b> — 2 дня\n\n"
        "Теперь создай клан — подписка применится автоматически 👇",
        reply_markup=presub_after_pay_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("presub_plan_"))
async def presub_plan_handler(callback: CallbackQuery):
    plan = callback.data.split("_")[2]
    if plan not in PLAN_NAMES:
        await callback.answer()
        return
    text = (
        f"💎 <b>{PLAN_NAMES[plan]}</b>\n\n"
        f"⭐ Звёздами: <b>{PLAN_PRICES_STARS[plan]} Stars</b>\n"
        f"💎 TON/USDT: <b>{PLAN_PRICES_USDT[plan]} USDT</b> <i>(скидка 15%!)</i>\n\n"
        "Выбери способ оплаты 👇"
    )
    await safe_edit_text(callback.message, text, reply_markup=presub_payment_kb(plan))
    await callback.answer()


@router.callback_query(F.data.startswith("presub_stars_"))
async def presub_stars_handler(callback: CallbackQuery, bot: Bot):
    plan = callback.data.split("_")[2]
    if plan not in PLAN_NAMES:
        await callback.answer()
        return
    stars = PLAN_PRICES_STARS[plan]
    await callback.message.delete()
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Подписка для клана: {PLAN_NAMES[plan]}",
        description=f"30 дней, до {PLAN_LIMITS[plan]} участников.",
        payload=f"clan_precreate_{plan}",
        currency="XTR",
        prices=[LabeledPrice(label=PLAN_NAMES[plan], amount=stars)],
    )
    await callback.answer()


@router.callback_query(F.data.startswith("presub_ton_") & ~F.data.startswith("presub_ton_check_"))
async def presub_ton_handler(callback: CallbackQuery):
    plan = callback.data.split("_")[2]
    if plan not in PLAN_NAMES:
        await callback.answer()
        return
    order = await create_ton_order(clan_id=0, user_id=callback.from_user.id, plan=plan)
    usdt = order["amount_usdt"]
    memo = order["memo"]
    expires = order["expires_at"][11:16]
    text = (
        f"💎 <b>Оплата через TON</b>\n\n"
        f"План: <b>{PLAN_NAMES[plan]}</b>\n"
        f"Скидка 15% за оплату криптой!\n\n"
        f"1️⃣ Отправь <b>USDT (TON)</b> на кошелёк:\n"
        f"<code>{TON_WALLET}</code>\n\n"
        f"2️⃣ Сумма:\n"
        f"<code>{usdt:.2f}</code> USDT\n\n"
        f"3️⃣ Мемо (обязательно!):\n"
        f"<code>{memo}</code>\n\n"
        f"⏱ Заказ действителен до {expires} UTC\n\n"
        "После оплаты нажми «Проверить» ✅"
    )
    await safe_edit_text(callback.message, text, reply_markup=presub_ton_check_kb(order["id"], plan))
    await callback.answer()


@router.callback_query(F.data.startswith("presub_ton_check_"))
async def presub_ton_check_handler(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[3])
    order = await get_ton_order(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    if order["status"] == "paid":
        await callback.answer("✅ Уже оплачено!", show_alert=True)
        return
    if order["status"] == "expired" or order["expires_at"] < datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"):
        await callback.answer("⏱ Заказ истёк. Создай новый.", show_alert=True)
        return
    await callback.answer("🔄 Проверяю блокчейн...")
    found, tx_hash = await check_ton_payment(order["memo"], order["amount_usdt"])
    if found:
        result = await mark_ton_order_paid(order_id, tx_hash or "")
        if result and result["type"] == "credit":
            await safe_edit_text(
                callback.message,
                f"✅ <b>Оплата подтверждена!</b>\n\n"
                f"План: <b>{PLAN_NAMES[order['plan']]}</b>\n"
                "Теперь создай клан — подписка применится автоматически 👇",
                reply_markup=presub_after_pay_kb(),
            )
    else:
        await callback.answer("❌ Оплата не найдена. Попробуй позже.", show_alert=True)


@router.callback_query(F.data.startswith("sub_ton_check_"))
async def sub_ton_check_handler(callback: CallbackQuery):
    clan = await get_user_clan(callback.from_user.id)
    if not clan:
        await callback.answer("Нет прав", show_alert=True)
        return
    order_id = int(callback.data.split("_")[3])
    order = await get_ton_order(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    if order["status"] == "paid":
        await callback.answer("✅ Уже оплачено!", show_alert=True)
        return
    if order["status"] == "expired" or order["expires_at"] < datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"):
        await callback.answer("⏱ Заказ истёк. Создай новый.", show_alert=True)
        return

    await callback.answer("🔄 Проверяю блокчейн...")
    found, tx_hash = await check_ton_payment(order["memo"], order["amount_usdt"])
    if found:
        result = await mark_ton_order_paid(order_id, tx_hash or "")
        if result:
            clan_id, plan = result
            await safe_edit_text(
                callback.message,
                f"✅ <b>Оплата подтверждена!</b>\n\n"
                f"План: <b>{PLAN_NAMES[plan]}</b>\n"
                "Подписка активирована на 30 дней!\n"
                "Можешь приглашать участников 🎉",
                reply_markup=sub_back_kb(),
            )
    else:
        await callback.answer("❌ Оплата не найдена. Попробуй позже.", show_alert=True)
