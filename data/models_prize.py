import json
from datetime import datetime, timedelta

import aiosqlite

from data.database import DB_PATH

# Админ вводит время по МСК, в БД храним UTC (как и остальной проект).
MSK_OFFSET_HOURS = 3
_DT_FMT = "%Y-%m-%d %H:%M:%S"

_COLS = (
    "id, title, prize_pool, photo1, photo2, photo3, post_text, post_entities, "
    "button_emoji, launch_at, wipe_days, hidden, pinned, created_at"
)


def entities_to_json(entities) -> str | None:
    if not entities:
        return None
    return json.dumps([e.model_dump() for e in entities])


def json_to_entities(data: str | None):
    if not data:
        return None
    from aiogram.types import MessageEntity
    return [MessageEntity(**e) for e in json.loads(data)]


# ── Дата выхода ───────────────────────────────────────────────────────────────

def parse_launch_input(text: str) -> str:
    """'08.09 18:00' | '8.9.2026 18:00' (МСК) -> 'YYYY-MM-DD HH:MM:SS' (UTC)."""
    try:
        return _parse_launch_input(text)
    except ValueError:
        raise
    except Exception:
        raise ValueError("Не понял дату. Формат: 08.09 18:00")


def _parse_launch_input(text: str) -> str:
    parts = text.strip().split()
    if len(parts) != 2:
        raise ValueError("Нужны дата и время: 08.09 18:00")
    date_part, time_part = parts

    d = date_part.split(".")
    if len(d) not in (2, 3):
        raise ValueError("Дата в формате ДД.ММ или ДД.ММ.ГГГГ")
    try:
        day, month = int(d[0]), int(d[1])
    except ValueError:
        raise ValueError("Дата в формате ДД.ММ, напр. 08.09")
    now_msk = datetime.utcnow() + timedelta(hours=MSK_OFFSET_HOURS)
    if len(d) == 3:
        year = int(d[2])
        if year < 100:
            year += 2000
    else:
        year = now_msk.year

    t = time_part.split(":")
    if len(t) != 2:
        raise ValueError("Время в формате ЧЧ:ММ")
    try:
        hour, minute = int(t[0]), int(t[1])
    except ValueError:
        raise ValueError("Время в формате ЧЧ:ММ, напр. 18:00")

    try:
        dt_msk = datetime(year, month, day, hour, minute)
    except ValueError:
        raise ValueError("Неверная дата или время")
    # Год не указали, а дата уже прошла — значит имелся в виду следующий год.
    if len(d) == 2 and dt_msk < now_msk - timedelta(days=1):
        dt_msk = dt_msk.replace(year=year + 1)

    dt_utc = dt_msk - timedelta(hours=MSK_OFFSET_HOURS)
    return dt_utc.strftime(_DT_FMT)


def format_launch(launch_at: str | None) -> str:
    if not launch_at:
        return "—"
    try:
        dt_utc = datetime.fromisoformat(launch_at)
    except ValueError:
        return launch_at
    dt_msk = dt_utc + timedelta(hours=MSK_OFFSET_HOURS)
    return dt_msk.strftime("%d.%m %H:%M") + " МСК"


def format_launch_short(launch_at: str | None) -> str:
    if not launch_at:
        return ""
    try:
        dt_utc = datetime.fromisoformat(launch_at)
    except ValueError:
        return ""
    return (dt_utc + timedelta(hours=MSK_OFFSET_HOURS)).strftime("%d.%m %H:%M")


# ── Чтение ────────────────────────────────────────────────────────────────────

_ORDER = (
    "ORDER BY COALESCE(pinned, 0) DESC, (launch_at IS NULL) ASC, launch_at ASC, id DESC"
)
_NOT_EXPIRED = (
    "(launch_at IS NULL OR wipe_days IS NULL "
    "OR datetime(launch_at, '+' || wipe_days || ' days') > datetime('now'))"
)


async def get_prize_servers() -> list[dict]:
    """Для пользователей: только видимые и не завершённые, ближайший выход сверху."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"SELECT {_COLS} FROM prize_servers "
            f"WHERE COALESCE(hidden, 0) = 0 AND {_NOT_EXPIRED} {_ORDER}"
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_prize_servers_admin() -> list[dict]:
    """Для админ/модер панели: все сервера, включая скрытые и завершённые."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"SELECT {_COLS} FROM prize_servers {_ORDER}"
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_prize_server(server_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"SELECT {_COLS} FROM prize_servers WHERE id = ?",
            (server_id,),
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


def is_expired(server: dict) -> bool:
    launch_at, wipe_days = server.get("launch_at"), server.get("wipe_days")
    if not launch_at or not wipe_days:
        return False
    try:
        end = datetime.fromisoformat(launch_at) + timedelta(days=int(wipe_days))
    except (ValueError, TypeError):
        return False
    return end <= datetime.utcnow()


# ── Запись ────────────────────────────────────────────────────────────────────

async def add_prize_server(
    title: str,
    prize_pool: str | None,
    photo1: str | None,
    photo2: str | None,
    photo3: str | None,
    post_text: str | None,
    post_entities: str | None,
    button_emoji: str | None = None,
    launch_at: str | None = None,
    wipe_days: int | None = None,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO prize_servers "
            "(title, prize_pool, photo1, photo2, photo3, post_text, post_entities, "
            " button_emoji, launch_at, wipe_days, hidden) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
            (title, prize_pool, photo1, photo2, photo3, post_text, post_entities,
             button_emoji, launch_at, wipe_days),
        )
        await db.commit()
        return cur.lastrowid


async def update_prize_server(server_id: int, **fields):
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [server_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE prize_servers SET {set_clause} WHERE id = ?", values)
        await db.commit()


async def set_prize_pinned(server_id: int, pinned: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE prize_servers SET pinned = ? WHERE id = ?",
            (1 if pinned else 0, server_id),
        )
        await db.commit()


async def delete_prize_server(server_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM prize_servers WHERE id = ?", (server_id,))
        await db.commit()


async def delete_expired_prize_servers() -> int:
    """Удаляет сервера, у которых вайп уже закончился (launch_at + wipe_days)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM prize_servers "
            "WHERE launch_at IS NOT NULL AND wipe_days IS NOT NULL "
            "  AND datetime(launch_at, '+' || wipe_days || ' days') <= datetime('now')"
        )
        await db.commit()
        return cur.rowcount or 0
