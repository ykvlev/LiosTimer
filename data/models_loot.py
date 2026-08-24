import aiosqlite
from datetime import datetime, timedelta

from data.database import DB_PATH

DEFAULT_MINUTES: dict[str, int] = {
    "blue": 120,
    "purple": 180,
}

CARD_EMOJI: dict[str, str] = {
    "blue": "🔵",
    "purple": "🟣",
}

CARD_EMOJI_HTML: dict[str, str] = {
    "blue":   '<tg-emoji emoji-id="5305359387471149323">🔵</tg-emoji>',
    "purple": '<tg-emoji emoji-id="5307762520457507728">🟣</tg-emoji>',
}

CARD_NAMES: dict[str, str] = {
    "blue": "Синяя",
    "purple": "Фиолетовая",
}

LOOT_ITEM_LABELS: dict[str, tuple[str, str]] = {
    "tank":    ("🚗", "Танк"),
    "avenger": ("😈", "Мститель"),
    "egg":     ("🥚", "Монст Егг"),
    "heli":    ("🚁", "Вертолет"),
    "patrol":  ("🪂", "Десант"),
    "cargo":   ("🚢", "Карго"),
    "medal":   ("🏅", "Медаль"),
}

LOOT_ITEM_EMOJI_HTML: dict[str, str] = {
    "tank":    '<tg-emoji emoji-id="5325863428198265230">🚗</tg-emoji>',
    "avenger": '<tg-emoji emoji-id="5341780894824831113">😈</tg-emoji>',
    "egg":     '<tg-emoji emoji-id="5341313306030283326">🥚</tg-emoji>',
    "heli":    '<tg-emoji emoji-id="5323546495205536651">🚁</tg-emoji>',
    "patrol":  '<tg-emoji emoji-id="5386642223368530459">🪂</tg-emoji>',
    "cargo":   '<tg-emoji emoji-id="5323526957399308323">🚢</tg-emoji>',
    "medal":   '<tg-emoji emoji-id="5305349315772839031">🏅</tg-emoji>',
}

LOCATIONS: dict[str, dict] = {
    "institute":  {"name": "Институт",             "emoji": "🏛️",  "slots": 1, "fixed": ["blue"]},
    "factory":    {"name": "Завод",                "emoji": "🏭",  "slots": 1, "fixed": ["blue"]},
    "airport":    {"name": "Аэропорт",             "emoji": "✈️",  "slots": 2, "fixed": None},
    "harbor":     {"name": "Харбер",               "emoji": "⚓",  "slots": 2, "fixed": None},
    "lab":        {"name": "Лаборатория",           "emoji": "🔬",  "slots": 2, "fixed": None},
    "milka":      {"name": "Милка",                "emoji": "🏪",  "slots": 3, "fixed": None},
    "bunker_low": {"name": "Бункер нижний",          "emoji": "💣",  "slots": 1, "fixed": None},
    "bunker_high":{"name": "Бункер верхний",         "emoji": "🔝",  "slots": 1, "fixed": None},
    "aes":        {"name": "АЕС",                  "emoji": "☢️",  "slots": 3, "fixed": None},
    "ship":       {"name": "Корабль",              "emoji": "🚢",  "slots": 2, "fixed": ["blue", "purple"]},
    "bandit":     {"name": "Бандитка",             "emoji": "🤠",  "slots": 1, "fixed": None},
}


async def get_user_cd_minutes(user_id: int) -> dict[str, int]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT blue_minutes, purple_minutes FROM loot_settings WHERE user_id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return dict(DEFAULT_MINUTES)
    return {"blue": row["blue_minutes"], "purple": row["purple_minutes"]}


async def set_user_cd_minutes(user_id: int, card_type: str, minutes: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO loot_settings (user_id, blue_minutes, purple_minutes)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                blue_minutes   = CASE WHEN ? = 'blue'   THEN ? ELSE blue_minutes   END,
                purple_minutes = CASE WHEN ? = 'purple' THEN ? ELSE purple_minutes END
            """,
            (user_id,
             minutes if card_type == "blue" else DEFAULT_MINUTES["blue"],
             minutes if card_type == "purple" else DEFAULT_MINUTES["purple"],
             card_type, minutes,
             card_type, minutes),
        )
        await db.commit()


EVENT_DEFAULTS: dict[str, int] = {
    "tank":    360,
    "avenger": 360,
    "egg":     360,
    "heli":    375,
    "patrol":  360,
    "cargo":   390,
    "medal":   360,
}


async def get_user_event_cd(user_id: int, event: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT minutes FROM loot_event_settings WHERE user_id = ? AND event = ?",
            (user_id, event),
        ) as cur:
            row = await cur.fetchone()
    return row["minutes"] if row else EVENT_DEFAULTS[event]


async def set_user_event_cd(user_id: int, event: str, minutes: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO loot_event_settings (user_id, event, minutes)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, event) DO UPDATE SET minutes = excluded.minutes
            """,
            (user_id, event, minutes),
        )
        await db.commit()


def parse_hm(text: str) -> int | None:
    text = text.strip()
    if ":" in text:
        parts = text.split(":")
        if len(parts) == 2:
            try:
                h, m = int(parts[0]), int(parts[1])
                if 0 <= h <= 23 and 0 <= m <= 59 and (h > 0 or m > 0):
                    return h * 60 + m
            except ValueError:
                pass
        return None
    try:
        val = int(text)
        if 1 <= val <= 1440:
            return val
    except ValueError:
        pass
    return None


def format_minutes(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    if m == 0:
        return f"{h}ч"
    return f"{h}ч {m:02d}мин"


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


async def get_all_slots(user_id: int) -> dict[tuple[str, int], dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM loot_rooms WHERE user_id = ?",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
    result = {}
    for r in rows:
        d = dict(r)
        d["seconds_left"] = _seconds_left(d.get("ready_at"))
        result[(d["location"], d["slot"])] = d
    return result


async def get_slot(user_id: int, location: str, slot: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM loot_rooms WHERE user_id = ? AND location = ? AND slot = ?",
            (user_id, location, slot),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return None
    d = dict(row)
    d["seconds_left"] = _seconds_left(d.get("ready_at"))
    return d


async def set_card_type(user_id: int, location: str, slot: int, card_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO loot_rooms (user_id, location, slot, card_type)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, location, slot) DO UPDATE SET card_type = excluded.card_type
            """,
            (user_id, location, slot, card_type),
        )
        await db.commit()


async def mark_looted(user_id: int, location: str, slot: int, notify_mode: str = "once") -> datetime:
    row = await get_slot(user_id, location, slot)
    card_type = row["card_type"] if row else "blue"
    cd_minutes = await get_user_cd_minutes(user_id)
    minutes = cd_minutes.get(card_type, DEFAULT_MINUTES[card_type])
    now = datetime.utcnow()
    ready_at = now + timedelta(minutes=minutes)
    fmt = "%Y-%m-%d %H:%M:%S"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO loot_rooms (user_id, location, slot, card_type, looted_at, ready_at, notify_mode, notified_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT(user_id, location, slot) DO UPDATE SET
                looted_at      = excluded.looted_at,
                ready_at       = excluded.ready_at,
                notify_mode    = excluded.notify_mode,
                notified_count = 0
            """,
            (user_id, location, slot, card_type, now.strftime(fmt), ready_at.strftime(fmt), notify_mode),
        )
        await db.commit()
    return ready_at


async def get_loot_ready_to_notify() -> tuple[list[dict], list[dict]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT user_id, location, slot, card_type, notify_mode
            FROM loot_rooms
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
            SELECT user_id, location, slot, card_type, notify_mode
            FROM loot_rooms
            WHERE notify_mode = 'twice'
              AND looted_at IS NOT NULL
              AND ready_at IS NOT NULL
              AND ready_at <= datetime('now', '-10 minutes')
              AND notified_count = 1
            """
        ) as cur:
            second = [dict(r) for r in await cur.fetchall()]
    return first, second


async def increment_loot_notified(user_id: int, location: str, slot: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE loot_rooms SET notified_count = notified_count + 1 WHERE user_id = ? AND location = ? AND slot = ?",
            (user_id, location, slot),
        )
        await db.commit()


def loot_notify_text(location: str, slot: int, card_type: str | None) -> str:
    if location in LOOT_ITEM_LABELS:
        _, name = LOOT_ITEM_LABELS[location]
        emoji_html = LOOT_ITEM_EMOJI_HTML[location]
        return f"🔔 <b>{emoji_html} {name}</b>\n\n{name} снова доступен!\nМожно идти лутать 🏃"
    if location in LOCATIONS:
        loc = LOCATIONS[location]
        card_emoji = CARD_EMOJI_HTML.get(card_type or "", "")
        card_name = CARD_NAMES.get(card_type or "", "")
        return (
            f"🔔 <b>{loc['emoji']} {loc['name']}</b>\n\n"
            f"Комната {slot + 1} {card_emoji} {card_name} — снова доступна!\n"
            f"Можно идти лутать 🏃"
        )
    return "🔔 <b>Лут доступен!</b>"


async def get_active_cd_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT COUNT(DISTINCT user_id), COUNT(*)
            FROM loot_rooms
            WHERE ready_at IS NOT NULL AND ready_at > datetime('now')
            """
        ) as cur:
            row = await cur.fetchone()
            personal_users = row[0] if row else 0
            personal_slots = row[1] if row else 0
        async with db.execute(
            """
            SELECT location, COUNT(*) FROM loot_rooms
            WHERE ready_at IS NOT NULL AND ready_at > datetime('now')
            GROUP BY location ORDER BY 2 DESC
            """
        ) as cur:
            personal_by_loc = {r[0]: r[1] for r in await cur.fetchall()}
        async with db.execute(
            """
            SELECT COUNT(DISTINCT clan_id), COUNT(*)
            FROM clan_loot_rooms
            WHERE ready_at IS NOT NULL AND ready_at > datetime('now')
            """
        ) as cur:
            row = await cur.fetchone()
            clan_clans = row[0] if row else 0
            clan_slots = row[1] if row else 0
        async with db.execute(
            """
            SELECT location, COUNT(*) FROM clan_loot_rooms
            WHERE ready_at IS NOT NULL AND ready_at > datetime('now')
            GROUP BY location ORDER BY 2 DESC
            """
        ) as cur:
            clan_by_loc = {r[0]: r[1] for r in await cur.fetchall()}
        async with db.execute(
            """
            SELECT COUNT(DISTINCT user_id), COUNT(*)
            FROM miniboss_rooms
            WHERE ready_at IS NOT NULL AND ready_at > datetime('now')
            """
        ) as cur:
            row = await cur.fetchone()
            mb_users = row[0] if row else 0
            mb_slots = row[1] if row else 0
        async with db.execute(
            """
            SELECT location, COUNT(*) FROM miniboss_rooms
            WHERE ready_at IS NOT NULL AND ready_at > datetime('now')
            GROUP BY location ORDER BY 2 DESC
            """
        ) as cur:
            mb_by_loc = {r[0]: r[1] for r in await cur.fetchall()}
        async with db.execute(
            """
            SELECT user_id FROM loot_rooms
            WHERE ready_at IS NOT NULL AND ready_at > datetime('now')
            UNION
            SELECT user_id FROM miniboss_rooms
            WHERE ready_at IS NOT NULL AND ready_at > datetime('now')
            """
        ) as cur:
            unique_users = len({r[0] for r in await cur.fetchall()})
    return {
        "unique_users": unique_users,
        "total_slots": personal_slots + clan_slots + mb_slots,
        "personal": {"users": personal_users, "slots": personal_slots, "by_loc": personal_by_loc},
        "clan":     {"clans": clan_clans,     "slots": clan_slots,     "by_loc": clan_by_loc},
        "miniboss": {"users": mb_users,       "slots": mb_slots,       "by_loc": mb_by_loc},
    }


async def reset_slot_timer(user_id: int, location: str, slot: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE loot_rooms SET looted_at = NULL, ready_at = NULL
            WHERE user_id = ? AND location = ? AND slot = ?
            """,
            (user_id, location, slot),
        )
        await db.commit()


async def reset_all_rooms(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM loot_rooms WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()
