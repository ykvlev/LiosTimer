import random
import aiosqlite
from datetime import datetime, timedelta

from data.database import DB_PATH

PLAN_LIMITS: dict[str, int] = {
    "duo":       2,
    "four":      4,
    "unlimited": 15,
}

PLAN_PRICES_USDT: dict[str, int] = {
    "duo":       2,
    "four":      3,
    "unlimited": 9,
}

PLAN_PRICES_STARS: dict[str, int] = {
    "duo":       115,
    "four":      175,
    "unlimited": 520,
}

PLAN_NAMES: dict[str, str] = {
    "duo":       "Duo — 2 игрока",
    "four":      "4 игрока",
    "unlimited": "Клан без лимитов (до 15)",
}

FREE_LIMIT = 0


def get_plan_limit(plan: str | None) -> int:
    return PLAN_LIMITS.get(plan or "", FREE_LIMIT)


async def get_clan_subscription(clan_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM clan_subscriptions WHERE clan_id = ? AND expires_at > datetime('now')",
            (clan_id,),
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def activate_subscription(clan_id: int, plan: str, days: int = 30, is_trial: bool = False):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT expires_at FROM clan_subscriptions WHERE clan_id = ? AND expires_at > datetime('now')",
            (clan_id,),
        ) as cur:
            existing = await cur.fetchone()
        if existing and not is_trial:
            base = datetime.fromisoformat(existing[0])
        else:
            base = datetime.utcnow()
        expires = base + timedelta(days=days)
        await db.execute(
            """
            INSERT INTO clan_subscriptions (clan_id, plan, expires_at, is_trial, trial_remind_count)
            VALUES (?, ?, ?, ?, 0)
            ON CONFLICT(clan_id) DO UPDATE SET
                plan = excluded.plan,
                expires_at = excluded.expires_at,
                is_trial = excluded.is_trial,
                trial_remind_count = 0
            """,
            (clan_id, plan, expires.strftime("%Y-%m-%d %H:%M:%S"), 1 if is_trial else 0),
        )
        await db.commit()


async def create_ton_order(clan_id: int, user_id: int, plan: str) -> dict:
    memo = str(random.randint(10000000, 99999999))
    amount = PLAN_PRICES_USDT[plan]
    now = datetime.utcnow()
    expires = now + timedelta(minutes=30)
    fmt = "%Y-%m-%d %H:%M:%S"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE ton_orders SET status = 'expired' WHERE clan_id = ? AND status = 'pending'",
            (clan_id,),
        )
        await db.execute(
            """
            INSERT INTO ton_orders (clan_id, user_id, plan, amount_usdt, memo, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (clan_id, user_id, plan, amount, memo, expires.strftime(fmt)),
        )
        async with db.execute("SELECT last_insert_rowid() AS id") as cur:
            order_id = (await cur.fetchone())[0]
        await db.commit()
    return {
        "id": order_id,
        "clan_id": clan_id,
        "user_id": user_id,
        "plan": plan,
        "amount_usdt": amount,
        "memo": memo,
        "expires_at": expires.strftime(fmt),
    }


async def get_ton_order(order_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM ton_orders WHERE id = ?", (order_id,)) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def get_pending_clan_ton_order(clan_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM ton_orders
            WHERE clan_id = ? AND status = 'pending' AND expires_at > datetime('now')
            ORDER BY created_at DESC LIMIT 1
            """,
            (clan_id,),
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def get_all_pending_ton_orders() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM ton_orders WHERE status = 'pending' AND expires_at > datetime('now')"
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def mark_ton_order_paid(order_id: int, tx_hash: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT clan_id, user_id, plan FROM ton_orders WHERE id = ?", (order_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        clan_id, user_id, plan = row[0], row[1], row[2]
        await db.execute(
            "UPDATE ton_orders SET status = 'paid', tx_hash = ?, verified_at = datetime('now') WHERE id = ?",
            (tx_hash, order_id),
        )
        await db.commit()
    if clan_id > 0:
        await activate_subscription(clan_id, plan)
        return {"type": "activate", "clan_id": clan_id, "user_id": user_id, "plan": plan}
    else:
        await store_user_sub_credit(user_id, plan)
        return {"type": "credit", "user_id": user_id, "plan": plan}


async def store_user_sub_credit(user_id: int, plan: str, hours: int = 24, is_trial: bool = False, days: int = 30):
    expires = datetime.utcnow() + timedelta(hours=hours)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_sub_credits (user_id, plan, expires_at, is_trial, days)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                plan = excluded.plan,
                expires_at = excluded.expires_at,
                is_trial = excluded.is_trial,
                days = excluded.days
            """,
            (user_id, plan, expires.strftime("%Y-%m-%d %H:%M:%S"), 1 if is_trial else 0, days),
        )
        await db.commit()


async def get_user_sub_credit(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM user_sub_credits WHERE user_id = ? AND expires_at > datetime('now')",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def consume_user_sub_credit(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT plan, is_trial, days FROM user_sub_credits WHERE user_id = ? AND expires_at > datetime('now')",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        result = {"plan": row["plan"], "is_trial": bool(row["is_trial"]), "days": row["days"]}
        await db.execute("DELETE FROM user_sub_credits WHERE user_id = ?", (user_id,))
        await db.commit()
    return result


async def has_used_trial(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM user_trials WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
    return row is not None


async def mark_trial_used(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO user_trials (user_id) VALUES (?)", (user_id,)
        )
        await db.commit()


async def get_trial_subs_for_reminder() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT cs.clan_id, cs.plan, cs.expires_at, cs.trial_remind_count, c.owner_id, c.name
            FROM clan_subscriptions cs
            JOIN clans c ON c.id = cs.clan_id
            WHERE cs.is_trial = 1
              AND cs.expires_at > datetime('now')
              AND (
                  (cs.trial_remind_count = 0 AND cs.expires_at <= datetime('now', '+48 hours'))
                  OR
                  (cs.trial_remind_count = 1 AND cs.expires_at <= datetime('now', '+24 hours'))
              )
            """
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def increment_trial_remind_count(clan_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE clan_subscriptions SET trial_remind_count = trial_remind_count + 1 WHERE clan_id = ?",
            (clan_id,),
        )
        await db.commit()


async def expire_old_ton_orders():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE ton_orders SET status = 'expired' WHERE status = 'pending' AND expires_at <= datetime('now')"
        )
        await db.commit()
