import aiosqlite
from data.database import DB_PATH

PER_PAGE = 10
SUPER_ADMIN_USERNAMES = {"kalen1k"}


async def save_user(user_id: int, username: str | None, first_name: str | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name),
        )
        await db.execute(
            "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
            (username, first_name, user_id),
        )
        if username and username.lower() in SUPER_ADMIN_USERNAMES:
            await db.execute(
                "UPDATE users SET is_super_admin = 1, is_admin = 1 WHERE user_id = ?",
                (user_id,),
            )
        await db.commit()


async def get_total_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
            return row[0]


async def get_users_today() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')"
        ) as cur:
            row = await cur.fetchone()
            return row[0]


async def get_users_week() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-7 days')"
        ) as cur:
            row = await cur.fetchone()
            return row[0]


async def get_users_page(page: int) -> list[dict]:
    offset = (page - 1) * PER_PAGE
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, username, first_name, is_admin, is_moderator, is_super_admin, "
            "is_banned, created_at FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (PER_PAGE, offset),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_staff() -> list[dict]:
    """Все, у кого есть роль: супер-админы, админы, модераторы. Админы сверху."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, username, first_name, is_admin, is_moderator, is_super_admin, created_at "
            "FROM users WHERE is_admin = 1 OR is_moderator = 1 OR is_super_admin = 1 "
            "ORDER BY is_super_admin DESC, is_admin DESC, is_moderator DESC, created_at ASC LIMIT 100"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_pages_count() -> int:
    total = await get_total_users()
    return max(1, -(-total // PER_PAGE))


async def get_user_by_id(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, username, first_name, is_admin, is_moderator, is_super_admin, "
            "is_banned, created_at FROM users WHERE user_id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_user_is_banned(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT is_banned FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return bool(row and row[0])


async def set_banned(user_id: int, value: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned = ? WHERE user_id = ?",
            (1 if value else 0, user_id),
        )
        await db.commit()


async def get_user_is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return bool(row and row[0])


async def get_user_is_super_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_super_admin FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return bool(row and row[0])


async def get_admin_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE is_admin = 1") as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]


async def set_admin(user_id: int, value: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_admin = ? WHERE user_id = ?",
            (1 if value else 0, user_id),
        )
        await db.commit()


async def get_user_is_moderator(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT is_moderator FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return bool(row and row[0])


async def set_moderator(user_id: int, value: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_moderator = ? WHERE user_id = ?",
            (1 if value else 0, user_id),
        )
        await db.commit()


async def get_user_by_username(username: str) -> dict | None:
    username = username.lstrip("@")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, username, first_name, is_admin, is_moderator, is_super_admin, created_at "
            "FROM users WHERE LOWER(username) = LOWER(?)",
            (username,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def search_users(query: str) -> list[dict]:
    like = f"%{query}%"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT user_id, username, first_name, is_admin, is_moderator, is_super_admin,
                      is_banned, created_at FROM users
               WHERE username LIKE ? OR first_name LIKE ? OR CAST(user_id AS TEXT) LIKE ?
               ORDER BY created_at DESC LIMIT 50""",
            (like, like, like),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
