import aiosqlite

from data.database import DB_PATH

NOTIF_KEYS = {
    "loot":       "🎮 Лут готов",
    "wipe_start": "🧹 Вайп начался",
    "wipe_1h":    "⏰ Вайп через 1ч",
}


async def get_notif_settings(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT loot, wipe_start, wipe_1h FROM user_notifications WHERE user_id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    if row:
        return dict(row)
    return {"loot": 1, "wipe_start": 1, "wipe_1h": 1}


async def toggle_notif(user_id: int, key: str) -> int:
    settings = await get_notif_settings(user_id)
    new_val = 0 if settings[key] else 1
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_notifications (user_id, loot, wipe_start, wipe_1h)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET {} = excluded.{}
            """.format(key, key),
            (
                user_id,
                new_val if key == "loot" else settings["loot"],
                new_val if key == "wipe_start" else settings["wipe_start"],
                new_val if key == "wipe_1h" else settings["wipe_1h"],
            ),
        )
        await db.commit()
    return new_val


async def is_notif_enabled(user_id: int, key: str) -> bool:
    settings = await get_notif_settings(user_id)
    return bool(settings.get(key, 1))
