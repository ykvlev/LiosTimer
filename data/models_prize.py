import json
import aiosqlite

from data.database import DB_PATH


def entities_to_json(entities) -> str | None:
    if not entities:
        return None
    return json.dumps([e.model_dump() for e in entities])


def json_to_entities(data: str | None):
    if not data:
        return None
    from aiogram.types import MessageEntity
    return [MessageEntity(**e) for e in json.loads(data)]


async def get_prize_servers() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, title, prize_pool, photo1, photo2, photo3, post_text, post_entities, button_emoji, created_at "
            "FROM prize_servers ORDER BY id DESC"
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_prize_server(server_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, title, prize_pool, photo1, photo2, photo3, post_text, post_entities, button_emoji "
            "FROM prize_servers WHERE id = ?",
            (server_id,),
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def add_prize_server(
    title: str,
    prize_pool: str | None,
    photo1: str | None,
    photo2: str | None,
    photo3: str | None,
    post_text: str | None,
    post_entities: str | None,
    button_emoji: str | None = None,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO prize_servers (title, prize_pool, photo1, photo2, photo3, post_text, post_entities, button_emoji) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, prize_pool, photo1, photo2, photo3, post_text, post_entities, button_emoji),
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


async def delete_prize_server(server_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM prize_servers WHERE id = ?", (server_id,))
        await db.commit()
