import aiosqlite

DB_PATH = "data/bot.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id    INTEGER PRIMARY KEY,
                username   TEXT,
                first_name TEXT,
                is_admin   INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_super_admin INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_moderator INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
        except Exception:
            pass
        for uname in ("KALEN1K",):
            await db.execute(
                "UPDATE users SET is_super_admin = 1, is_admin = 1 WHERE LOWER(username) = LOWER(?)",
                (uname,),
            )
        await db.execute("""
            CREATE TABLE IF NOT EXISTS wipe_servers (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                name       TEXT NOT NULL,
                wipe_at    TIMESTAMP NOT NULL,
                is_active  INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        try:
            await db.execute("ALTER TABLE wipe_servers ADD COLUMN is_active INTEGER DEFAULT 0")
        except Exception:
            pass
        for col in [
            "had_pending INTEGER DEFAULT 0",
            "wipe_start_notified INTEGER DEFAULT 0",
        ]:
            try:
                await db.execute(f"ALTER TABLE wipe_servers ADD COLUMN {col}")
            except Exception:
                pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS prize_servers (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                title         TEXT NOT NULL,
                prize_pool    TEXT,
                photo1        TEXT,
                photo2        TEXT,
                photo3        TEXT,
                post_text     TEXT,
                post_entities TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for col_def in [
            "prize_pool TEXT", "photo1 TEXT", "photo2 TEXT",
            "photo3 TEXT", "post_text TEXT", "post_entities TEXT",
            "button_emoji TEXT",
            "launch_at TIMESTAMP", "wipe_days INTEGER",
            "hidden INTEGER DEFAULT 0",
        ]:
            try:
                await db.execute(f"ALTER TABLE prize_servers ADD COLUMN {col_def}")
            except Exception:
                pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS loot_rooms (
                user_id        INTEGER NOT NULL,
                location       TEXT NOT NULL,
                slot           INTEGER NOT NULL,
                card_type      TEXT,
                looted_at      TIMESTAMP,
                ready_at       TIMESTAMP,
                notify_mode    TEXT DEFAULT 'once',
                notified_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, location, slot)
            )
        """)
        for col in [
            "notify_mode TEXT DEFAULT 'once'",
            "notified_count INTEGER DEFAULT 0",
        ]:
            try:
                await db.execute(f"ALTER TABLE loot_rooms ADD COLUMN {col}")
            except Exception:
                pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS loot_settings (
                user_id        INTEGER PRIMARY KEY,
                blue_minutes   INTEGER DEFAULT 120,
                purple_minutes INTEGER DEFAULT 180
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS global_settings (
                key    TEXT PRIMARY KEY,
                value  TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clan_loot_rooms (
                clan_id        INTEGER NOT NULL,
                location       TEXT NOT NULL,
                slot           INTEGER NOT NULL,
                card_type      TEXT,
                looted_at      TIMESTAMP,
                ready_at       TIMESTAMP,
                notify_mode    TEXT DEFAULT 'once',
                notified_count INTEGER DEFAULT 0,
                looted_by      INTEGER,
                PRIMARY KEY (clan_id, location, slot)
            )
        """)
        try:
            await db.execute("ALTER TABLE clan_loot_rooms ADD COLUMN looted_by INTEGER")
        except Exception:
            pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clan_loot_settings (
                clan_id        INTEGER PRIMARY KEY,
                blue_minutes   INTEGER NOT NULL DEFAULT 120,
                purple_minutes INTEGER NOT NULL DEFAULT 180
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_menu_photo (
                user_id  INTEGER PRIMARY KEY,
                file_id  TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS loot_event_settings (
                user_id  INTEGER NOT NULL,
                event    TEXT NOT NULL,
                minutes  INTEGER NOT NULL,
                PRIMARY KEY (user_id, event)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clans (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT NOT NULL UNIQUE,
                tag            TEXT NOT NULL UNIQUE,
                owner_id       INTEGER NOT NULL,
                clan_server_id INTEGER,
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        try:
            await db.execute("ALTER TABLE clans ADD COLUMN clan_server_id INTEGER")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE clans ADD COLUMN photo TEXT")
        except Exception:
            pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clan_loot_events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                clan_id    INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                event_name TEXT NOT NULL,
                looted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ready_at   TIMESTAMP NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clan_members (
                user_id    INTEGER PRIMARY KEY,
                clan_id    INTEGER NOT NULL,
                role       TEXT DEFAULT 'member',
                joined_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (clan_id) REFERENCES clans(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_notifications (
                user_id        INTEGER PRIMARY KEY,
                loot           INTEGER DEFAULT 1,
                wipe_start     INTEGER DEFAULT 1,
                wipe_1h        INTEGER DEFAULT 1
            )
        """)
        try:
            await db.execute("ALTER TABLE wipe_servers ADD COLUMN wipe_1h_notified INTEGER DEFAULT 0")
        except Exception:
            pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clan_subscriptions (
                clan_id     INTEGER PRIMARY KEY,
                plan        TEXT NOT NULL,
                expires_at  TIMESTAMP NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_trials (
                user_id INTEGER PRIMARY KEY,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_sub_credits (
                user_id    INTEGER PRIMARY KEY,
                plan       TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)
        for col_def in ["is_trial INTEGER DEFAULT 0", "days INTEGER DEFAULT 30"]:
            try:
                await db.execute(f"ALTER TABLE user_sub_credits ADD COLUMN {col_def}")
            except Exception:
                pass
        for col_def in ["is_trial INTEGER DEFAULT 0", "trial_remind_count INTEGER DEFAULT 0"]:
            try:
                await db.execute(f"ALTER TABLE clan_subscriptions ADD COLUMN {col_def}")
            except Exception:
                pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ton_orders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                clan_id     INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                plan        TEXT NOT NULL,
                amount_usdt REAL NOT NULL,
                memo        TEXT NOT NULL UNIQUE,
                status      TEXT DEFAULT 'pending',
                tx_hash     TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                expires_at  TIMESTAMP NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                status     TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at  TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS support_messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id  INTEGER NOT NULL,
                sender     TEXT NOT NULL,
                admin_id   INTEGER,
                text       TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS miniboss_rooms (
                user_id        INTEGER NOT NULL,
                location       TEXT NOT NULL,
                looted_at      TIMESTAMP,
                ready_at       TIMESTAMP,
                notified_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, location)
            )
        """)
        await db.commit()
