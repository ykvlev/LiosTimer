import aiosqlite
from datetime import datetime, timedelta

from data.database import DB_PATH

TANK_CD_MINUTES = 360


async def get_tank_status(user_id: int) -> float | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT looted_at, ready_at FROM loot_rooms WHERE user_id = ? AND location = 'tank' AND slot = 0",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    if not row or not row["looted_at"]:
        return None
    if not row["ready_at"]:
        return 0.0
    dt = datetime.fromisoformat(row["ready_at"])
    return max(0.0, (dt - datetime.utcnow()).total_seconds())


async def get_tank(user_id: int) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT ready_at FROM loot_rooms WHERE user_id = ? AND location = 'tank' AND slot = 0",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    if not row or not row["ready_at"]:
        return 0.0
    dt = datetime.fromisoformat(row["ready_at"])
    return max(0.0, (dt - datetime.utcnow()).total_seconds())


async def mark_tank_looted(user_id: int, notify_mode: str = "once", cd_minutes: int | None = None):
    now = datetime.utcnow()
    ready_at = now + timedelta(minutes=cd_minutes if cd_minutes is not None else TANK_CD_MINUTES)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO loot_rooms (user_id, location, slot, card_type, looted_at, ready_at, notify_mode, notified_count)
            VALUES (?, 'tank', 0, 'tank', ?, ?, ?, 0)
            ON CONFLICT(user_id, location, slot) DO UPDATE SET
                looted_at      = excluded.looted_at,
                ready_at       = excluded.ready_at,
                notify_mode    = excluded.notify_mode,
                notified_count = 0
            """,
            (user_id, now.strftime("%Y-%m-%d %H:%M:%S"), ready_at.strftime("%Y-%m-%d %H:%M:%S"), notify_mode),
        )
        await db.commit()


async def reset_tank(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE loot_rooms SET looted_at = NULL, ready_at = NULL
            WHERE user_id = ? AND location = 'tank' AND slot = 0
            """,
            (user_id,),
        )
        await db.commit()
