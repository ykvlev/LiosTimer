import aiosqlite

from data.database import DB_PATH

PER_PAGE = 10


async def get_open_ticket(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM support_tickets WHERE user_id = ? AND status = 'open' ORDER BY id DESC LIMIT 1",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def get_ticket(ticket_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM support_tickets WHERE id = ?", (ticket_id,)
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def open_ticket(user_id: int) -> dict:
    existing = await get_open_ticket(user_id)
    if existing:
        return existing
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO support_tickets (user_id) VALUES (?)", (user_id,)
        )
        await db.commit()
        ticket_id = cur.lastrowid
    return {"id": ticket_id, "user_id": user_id, "status": "open"}


async def close_ticket(ticket_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE support_tickets SET status = 'closed', closed_at = datetime('now') WHERE id = ?",
            (ticket_id,),
        )
        await db.commit()


async def add_message(ticket_id: int, sender: str, text: str, admin_id: int | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO support_messages (ticket_id, sender, admin_id, text) VALUES (?, ?, ?, ?)",
            (ticket_id, sender, admin_id, text),
        )
        await db.commit()


async def get_messages(ticket_id: int, limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM (SELECT * FROM support_messages WHERE ticket_id = ? ORDER BY id DESC LIMIT ?) ORDER BY id",
            (ticket_id, limit),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_tickets_page(page: int, only_open: bool = True) -> list[dict]:
    offset = (page - 1) * PER_PAGE
    where = "WHERE t.status = 'open'" if only_open else ""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"""
            SELECT t.*,
                   (SELECT COUNT(*) FROM support_messages m WHERE m.ticket_id = t.id) AS msg_count,
                   (SELECT m.text FROM support_messages m WHERE m.ticket_id = t.id ORDER BY m.id DESC LIMIT 1) AS last_text
            FROM support_tickets t
            {where}
            ORDER BY t.id DESC LIMIT ? OFFSET ?
            """,
            (PER_PAGE, offset),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_tickets_pages_count(only_open: bool = True) -> int:
    where = "WHERE status = 'open'" if only_open else ""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(f"SELECT COUNT(*) FROM support_tickets {where}") as cur:
            row = await cur.fetchone()
    return max(1, -(-row[0] // PER_PAGE))


async def get_open_tickets_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM support_tickets WHERE status = 'open'") as cur:
            row = await cur.fetchone()
    return row[0]
