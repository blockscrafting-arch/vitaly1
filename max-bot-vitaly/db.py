"""SQLite: история публикаций и кликов по кнопкам."""
import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent / "bot.db"


async def init_db() -> None:
    """Создаёт таблицы при первом запуске."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS publications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                post_text_hash TEXT,
                announce_text TEXT,
                topic TEXT,
                country TEXT,
                created_at DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS button_clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                user_id INTEGER,
                button_type TEXT,
                created_at DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS greeted_users (
                user_id INTEGER PRIMARY KEY,
                chat_id INTEGER,
                created_at DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()
    logger.info("DB initialized at %s", DB_PATH)


async def add_publication(
    timestamp: int,
    post_text_hash: str | None = None,
    announce_text: str | None = None,
    topic: str | None = None,
    country: str | None = None,
) -> None:
    """Добавляет запись о публикации."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO publications (timestamp, post_text_hash, announce_text, topic, country)
            VALUES (?, ?, ?, ?, ?)
            """,
            (timestamp, post_text_hash, announce_text, topic, country),
        )
        await db.commit()


async def get_last_publications(limit: int = 10) -> list[tuple[str | None, str | None]]:
    """Возвращает последние N записей (topic, country) для антиповтора."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT topic, country FROM publications
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
    return [(r["topic"], r["country"]) for r in rows]


async def record_button_click(user_id: int, button_type: str, timestamp: int | None = None) -> None:
    """Фиксирует нажатие кнопки (для аналитики)."""
    import time
    ts = timestamp or int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO button_clicks (timestamp, user_id, button_type) VALUES (?, ?, ?)",
            (ts, user_id, button_type),
        )
        await db.commit()


async def was_user_greeted(user_id: int) -> bool:
    """Проверяет, получал ли пользователь уже приветствие."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM greeted_users WHERE user_id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    return row is not None


async def set_user_greeted(user_id: int, chat_id: int | None = None) -> None:
    """Отмечает, что пользователю отправлено приветствие."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO greeted_users (user_id, chat_id) VALUES (?, ?)",
            (user_id, chat_id),
        )
        await db.commit()
