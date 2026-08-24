from datetime import datetime, timedelta

import aiosqlite

from data.database import DB_PATH


async def save_clan_loot_event(clan_id: int, user_id: int, event_name: str, cd_minutes: int):
    ready_at = (datetime.utcnow() + timedelta(minutes=cd_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            DELETE FROM clan_loot_events
            WHERE clan_id = ? AND user_id = ? AND event_name = ?
            """,
            (clan_id, user_id, event_name),
        )
        await db.execute(
            """
            INSERT INTO clan_loot_events (clan_id, user_id, event_name, ready_at)
            VALUES (?, ?, ?, ?)
            """,
            (clan_id, user_id, event_name, ready_at),
        )
        await db.commit()


async def get_clan_event_seconds(clan_id: int, event_name: str) -> float | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT MAX(ready_at) AS latest_ready
            FROM clan_loot_events
            WHERE clan_id = ? AND event_name = ?
            """,
            (clan_id, event_name),
        ) as cur:
            row = await cur.fetchone()
    if not row or not row["latest_ready"]:
        return None
    ready = datetime.fromisoformat(row["latest_ready"])
    secs = max(0.0, (ready - datetime.utcnow()).total_seconds())
    return secs if secs > 0 else None


async def get_clan_loot_events(clan_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT cle.user_id, cle.event_name, cle.ready_at,
                   u.first_name, u.username
            FROM clan_loot_events cle
            LEFT JOIN users u ON u.user_id = cle.user_id
            WHERE cle.clan_id = ?
              AND cle.ready_at > datetime('now')
            ORDER BY cle.ready_at ASC
            """,
            (clan_id,),
        ) as cur:
            rows = await cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        ready = datetime.fromisoformat(d["ready_at"])
        secs = max(0.0, (ready - datetime.utcnow()).total_seconds())
        d["seconds_left"] = secs
        result.append(d)
    return result
