import aiosqlite
from datetime import datetime, timedelta

from data.database import DB_PATH

WIPE_DURATION_HOURS = 346


def _hours_left(wipe_at: str) -> float:
    dt = datetime.fromisoformat(wipe_at)
    return max(0.0, (dt - datetime.utcnow()).total_seconds() / 3600)


def parse_hours_input(text: str) -> float:
    text = text.strip().replace(",", ".")
    if ":" in text:
        parts = text.split(":", 1)
        h = int(parts[0])
        m = int(parts[1])
        if m < 0 or m >= 60:
            raise ValueError
        return h + m / 60
    value = float(text)
    if value <= 0:
        raise ValueError
    return value


def format_hours(h: float) -> str:
    total_minutes = int(h * 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if hours > 0 and minutes > 0:
        return f"{hours}ч {minutes}мин"
    if hours > 0:
        return f"{hours}ч"
    return f"{minutes}мин"


def format_countdown(hours_left: float) -> str:
    if hours_left > WIPE_DURATION_HOURS:
        pending = hours_left - WIPE_DURATION_HOURS
        return f"старт через {format_hours(pending)}"
    if hours_left <= 0:
        return "вайп!"
    return format_hours(hours_left)


def _round_to_hour(dt: datetime) -> datetime:
    if dt.minute >= 30:
        return (dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return dt.replace(minute=0, second=0, microsecond=0)


async def add_server(user_id: int, name: str, hours: float, had_pending: bool = False) -> int:
    wipe_at = _round_to_hour(datetime.utcnow() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO wipe_servers (user_id, name, wipe_at, had_pending) VALUES (?, ?, ?, ?)",
            (user_id, name, wipe_at, int(had_pending)),
        )
        await db.commit()
        return cur.lastrowid


async def get_wipe_started_servers() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, user_id, name, wipe_at FROM wipe_servers
            WHERE had_pending = 1
              AND wipe_start_notified = 0
              AND wipe_at <= datetime('now', ? || ' hours')
              AND wipe_at > datetime('now')
            """,
            (str(WIPE_DURATION_HOURS),),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def mark_wipe_start_notified(server_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE wipe_servers SET wipe_start_notified = 1 WHERE id = ?",
            (server_id,),
        )
        await db.commit()


async def get_wipe_soon_servers() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, user_id, name FROM wipe_servers
            WHERE wipe_1h_notified = 0
              AND (julianday(wipe_at) - julianday('now')) * 24 BETWEEN 0.9 AND 1.1
            """
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def mark_wipe_1h_notified(server_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE wipe_servers SET wipe_1h_notified = 1 WHERE id = ?",
            (server_id,),
        )
        await db.commit()


async def get_servers(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, name, wipe_at, is_active FROM wipe_servers WHERE user_id = ? ORDER BY wipe_at ASC",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["hours_left"] = _hours_left(d["wipe_at"])
        result.append(d)
    return result


async def get_server(server_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, user_id, name, wipe_at, is_active FROM wipe_servers WHERE id = ?",
            (server_id,),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return None
    d = dict(row)
    d["hours_left"] = _hours_left(d["wipe_at"])
    return d


async def update_server_hours(server_id: int, hours: float):
    wipe_at = _round_to_hour(datetime.utcnow() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE wipe_servers SET wipe_at = ? WHERE id = ?",
            (wipe_at, server_id),
        )
        await db.commit()


async def delete_server(server_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM wipe_servers WHERE id = ?", (server_id,))
        await db.commit()


async def get_active_server(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, user_id, name, wipe_at FROM wipe_servers WHERE user_id = ? AND is_active = 1",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return None
    d = dict(row)
    d["hours_left"] = _hours_left(d["wipe_at"])
    d["is_active"] = True
    return d


async def set_active_server(user_id: int, server_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE wipe_servers SET is_active = 0 WHERE user_id = ?",
            (user_id,),
        )
        await db.execute(
            "UPDATE wipe_servers SET is_active = 1 WHERE id = ? AND user_id = ?",
            (server_id, user_id),
        )
        await db.commit()
