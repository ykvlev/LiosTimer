import aiosqlite

from data.database import DB_PATH


async def get_user_clan(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT c.id, c.name, c.tag, c.owner_id,
                   cm.role
            FROM clan_members cm
            JOIN clans c ON c.id = cm.clan_id
            WHERE cm.user_id = ?
            """,
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def get_clan_by_tag(tag: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM clans WHERE UPPER(tag) = UPPER(?)", (tag,)
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def get_clan_by_name(name: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM clans WHERE UPPER(name) = UPPER(?)", (name,)
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def create_clan(owner_id: int, name: str, tag: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT INTO clans (name, tag, owner_id) VALUES (?, ?, ?)",
            (name, tag.upper(), owner_id),
        )
        async with db.execute("SELECT last_insert_rowid() AS id") as cur:
            clan_id = (await cur.fetchone())["id"]
        await db.execute(
            "INSERT INTO clan_members (user_id, clan_id, role) VALUES (?, ?, 'owner')",
            (owner_id, clan_id),
        )
        await db.commit()
    return {"id": clan_id, "name": name, "tag": tag.upper(), "owner_id": owner_id}


async def join_clan(user_id: int, clan_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO clan_members (user_id, clan_id, role) VALUES (?, ?, 'member')",
            (user_id, clan_id),
        )
        await db.commit()


async def leave_clan(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT clan_id, role FROM clan_members WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return
        clan_id, role = row[0], row[1]
        await db.execute("DELETE FROM clan_members WHERE user_id = ?", (user_id,))
        if role == "owner":
            async with db.execute(
                "SELECT user_id FROM clan_members WHERE clan_id = ? LIMIT 1", (clan_id,)
            ) as cur:
                new_owner = await cur.fetchone()
            if new_owner:
                await db.execute(
                    "UPDATE clan_members SET role = 'owner' WHERE user_id = ?",
                    (new_owner[0],),
                )
                await db.execute(
                    "UPDATE clans SET owner_id = ? WHERE id = ?",
                    (new_owner[0], clan_id),
                )
            else:
                await db.execute("DELETE FROM clans WHERE id = ?", (clan_id,))
        await db.commit()


async def get_clan_photo(clan_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT photo FROM clans WHERE id = ?", (clan_id,)
        ) as cur:
            row = await cur.fetchone()
    return row["photo"] if row else None


async def set_clan_photo(clan_id: int, file_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE clans SET photo = ? WHERE id = ?", (file_id, clan_id)
        )
        await db.commit()


async def delete_clan_photo(clan_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE clans SET photo = NULL WHERE id = ?", (clan_id,)
        )
        await db.commit()


async def rename_clan(clan_id: int, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE clans SET name = ? WHERE id = ?", (name, clan_id))
        await db.commit()


async def retag_clan(clan_id: int, tag: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE clans SET tag = ? WHERE id = ?", (tag.upper(), clan_id))
        await db.commit()


async def get_clan_server_id(clan_id: int) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT clan_server_id FROM clans WHERE id = ?", (clan_id,)
        ) as cur:
            row = await cur.fetchone()
    return row["clan_server_id"] if row else None


async def set_clan_server(clan_id: int, server_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE clans SET clan_server_id = ? WHERE id = ?",
            (server_id, clan_id),
        )
        await db.commit()


async def remove_clan_server(clan_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE clans SET clan_server_id = NULL WHERE id = ?",
            (clan_id,),
        )
        await db.commit()


async def kick_member(user_id: int, clan_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM clan_members WHERE user_id = ? AND clan_id = ? AND role != 'owner'",
            (user_id, clan_id),
        )
        await db.commit()


async def set_member_role(user_id: int, clan_id: int, role: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE clan_members SET role = ? WHERE user_id = ? AND clan_id = ?",
            (role, user_id, clan_id),
        )
        await db.commit()


async def get_clan_members(clan_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT cm.user_id, cm.role, cm.joined_at,
                   u.username, u.first_name
            FROM clan_members cm
            LEFT JOIN users u ON u.user_id = cm.user_id
            WHERE cm.clan_id = ?
            ORDER BY cm.role DESC, cm.joined_at ASC
            """,
            (clan_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]
