import aiosqlite

from data.database import DB_PATH


async def get_menu_photo(user_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT file_id FROM user_menu_photo WHERE user_id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    return row["file_id"] if row else None


async def set_menu_photo(user_id: int, file_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_menu_photo (user_id, file_id)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET file_id = excluded.file_id
            """,
            (user_id, file_id),
        )
        await db.commit()


async def delete_menu_photo(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM user_menu_photo WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def get_global_photo() -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT value FROM global_settings WHERE key = 'menu_photo'",
        ) as cur:
            row = await cur.fetchone()
    return row["value"] if row else None


async def set_global_photo(file_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO global_settings (key, value) VALUES ('menu_photo', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (file_id,),
        )
        await db.commit()


async def delete_global_photo():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM global_settings WHERE key = 'menu_photo'",
        )
        await db.commit()
