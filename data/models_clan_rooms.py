import aiosqlite
from datetime import datetime, timedelta

from data.database import DB_PATH
from data.models_loot import DEFAULT_MINUTES, _seconds_left


async def get_clan_room_cd(clan_id: int) -> dict[str, int]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT blue_minutes, purple_minutes FROM clan_loot_settings WHERE clan_id = ?",
            (clan_id,),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return dict(DEFAULT_MINUTES)
    return {"blue": row["blue_minutes"], "purple": row["purple_minutes"]}


async def set_clan_room_cd(clan_id: int, card_type: str, minutes: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO clan_loot_settings (clan_id, blue_minutes, purple_minutes)
            VALUES (?, ?, ?)
            ON CONFLICT(clan_id) DO UPDATE SET
                blue_minutes   = CASE WHEN ? = 'blue'   THEN ? ELSE blue_minutes   END,
                purple_minutes = CASE WHEN ? = 'purple' THEN ? ELSE purple_minutes END
            """,
            (clan_id,
             minutes if card_type == "blue" else DEFAULT_MINUTES["blue"],
             minutes if card_type == "purple" else DEFAULT_MINUTES["purple"],
             card_type, minutes,
             card_type, minutes),
        )
        await db.commit()


async def get_clan_all_slots(clan_id: int) -> dict[tuple[str, int], dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM clan_loot_rooms WHERE clan_id = ?",
            (clan_id,),
        ) as cur:
            rows = await cur.fetchall()
    result = {}
    for r in rows:
        d = dict(r)
        d["seconds_left"] = _seconds_left(d.get("ready_at"))
        result[(d["location"], d["slot"])] = d
    return result


async def get_clan_slot(clan_id: int, location: str, slot: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM clan_loot_rooms WHERE clan_id = ? AND location = ? AND slot = ?",
            (clan_id, location, slot),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return None
    d = dict(row)
    d["seconds_left"] = _seconds_left(d.get("ready_at"))
    return d


async def set_clan_card_type(clan_id: int, location: str, slot: int, card_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO clan_loot_rooms (clan_id, location, slot, card_type)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(clan_id, location, slot) DO UPDATE SET card_type = excluded.card_type
            """,
            (clan_id, location, slot, card_type),
        )
        await db.commit()


async def mark_clan_looted(clan_id: int, location: str, slot: int,
                           notify_mode: str = "once", cd_minutes: dict | None = None,
                           looted_by: int | None = None,
                           minutes_override: int | None = None,
                           card_type_override: str | None = None) -> datetime:
    row = await get_clan_slot(clan_id, location, slot)
    card_type = card_type_override or (row["card_type"] if row else location)
    if minutes_override is not None:
        minutes = minutes_override
    else:
        effective_cd = cd_minutes or await get_clan_room_cd(clan_id)
        minutes = effective_cd.get(card_type, DEFAULT_MINUTES.get(card_type, 360))
    now = datetime.utcnow()
    ready_at = now + timedelta(minutes=minutes)
    fmt = "%Y-%m-%d %H:%M:%S"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO clan_loot_rooms (clan_id, location, slot, card_type,
                                         looted_at, ready_at, notify_mode, notified_count, looted_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            ON CONFLICT(clan_id, location, slot) DO UPDATE SET
                card_type      = excluded.card_type,
                looted_at      = excluded.looted_at,
                ready_at       = excluded.ready_at,
                notify_mode    = excluded.notify_mode,
                notified_count = 0,
                looted_by      = excluded.looted_by
            """,
            (clan_id, location, slot, card_type,
             now.strftime(fmt), ready_at.strftime(fmt), notify_mode, looted_by),
        )
        await db.commit()
    return ready_at


async def reset_clan_slot_timer(clan_id: int, location: str, slot: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE clan_loot_rooms SET looted_at = NULL, ready_at = NULL, notified_count = 0
            WHERE clan_id = ? AND location = ? AND slot = ?
            """,
            (clan_id, location, slot),
        )
        await db.commit()


async def get_clan_slot_looted_by(clan_id: int, location: str, slot: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT clr.looted_by, clr.ready_at, u.first_name, u.username
            FROM clan_loot_rooms clr
            LEFT JOIN users u ON u.user_id = clr.looted_by
            WHERE clr.clan_id = ? AND clr.location = ? AND clr.slot = ?
              AND clr.looted_at IS NOT NULL AND clr.ready_at > datetime('now')
            """,
            (clan_id, location, slot),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return None
    d = dict(row)
    ready = datetime.fromisoformat(d["ready_at"])
    d["seconds_left"] = max(0.0, (ready - datetime.utcnow()).total_seconds())
    return d


async def get_clan_rooms_ready_to_notify() -> tuple[list[dict], list[dict]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT clan_id, location, slot, card_type, notify_mode
            FROM clan_loot_rooms
            WHERE notify_mode != 'none'
              AND looted_at IS NOT NULL
              AND ready_at IS NOT NULL
              AND ready_at <= datetime('now')
              AND notified_count = 0
            """
        ) as cur:
            first = [dict(r) for r in await cur.fetchall()]
        async with db.execute(
            """
            SELECT clan_id, location, slot, card_type, notify_mode
            FROM clan_loot_rooms
            WHERE notify_mode = 'twice'
              AND looted_at IS NOT NULL
              AND ready_at IS NOT NULL
              AND ready_at <= datetime('now', '-10 minutes')
              AND notified_count = 1
            """
        ) as cur:
            second = [dict(r) for r in await cur.fetchall()]
    return first, second


async def increment_clan_loot_notified(clan_id: int, location: str, slot: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE clan_loot_rooms SET notified_count = notified_count + 1
            WHERE clan_id = ? AND location = ? AND slot = ?
            """,
            (clan_id, location, slot),
        )
        await db.commit()
