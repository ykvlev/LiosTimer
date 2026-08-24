import aiosqlite
from datetime import datetime, timedelta

from data.database import DB_PATH

MINIBOSS_CD_MINUTES = 30

MINIBOSS_ROOMS: dict[str, dict] = {
    "milka":      {"name": "Милка",       "emoji": "🏪"},
    "airport":    {"name": "Аэропорт",    "emoji": "✈️"},
    "harbor":     {"name": "Харбор",      "emoji": "⚓"},
    "aes":        {"name": "АЕС",         "emoji": "☢️"},
    "lab":        {"name": "Лаборатория", "emoji": "🔬"},
    "tradezone":  {"name": "Трейд зона",  "emoji": "🏬"},
    "bompshelter": {"name": "Бункер нижний", "emoji": "💣"},
}


def _seconds_left(ready_at: str | None) -> float:
    if not ready_at:
        return 0.0
    dt = datetime.fromisoformat(ready_at)
    return max(0.0, (dt - datetime.utcnow()).total_seconds())


def format_time_left(seconds: float) -> str:
    if seconds <= 0:
        return "доступен!"
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    if h > 0:
        return f"{h}ч {m:02d}мин"
    if m > 0:
        return f"{m}мин {s:02d}с"
    return f"{s}с"


async def get_all_miniboss(user_id: int) -> dict[str, dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM miniboss_rooms WHERE user_id = ?",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
    result = {}
    for r in rows:
        d = dict(r)
        d["seconds_left"] = _seconds_left(d.get("ready_at"))
        result[d["location"]] = d
    return result


async def mark_miniboss_looted(user_id: int, location: str) -> datetime:
    now = datetime.utcnow()
    ready_at = now + timedelta(minutes=MINIBOSS_CD_MINUTES)
    fmt = "%Y-%m-%d %H:%M:%S"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO miniboss_rooms (user_id, location, looted_at, ready_at, notified_count)
            VALUES (?, ?, ?, ?, 0)
            ON CONFLICT(user_id, location) DO UPDATE SET
                looted_at      = excluded.looted_at,
                ready_at       = excluded.ready_at,
                notified_count = 0
            """,
            (user_id, location, now.strftime(fmt), ready_at.strftime(fmt)),
        )
        await db.commit()
    return ready_at


async def reset_miniboss(user_id: int, location: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE miniboss_rooms
            SET looted_at = NULL, ready_at = NULL, notified_count = 0
            WHERE user_id = ? AND location = ?
            """,
            (user_id, location),
        )
        await db.commit()
