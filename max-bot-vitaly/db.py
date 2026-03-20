"""SQLite: каталог материалов, история публикаций, указатели ротации."""
import logging
import time
from typing import Any
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent / "bot.db"

CONTENT_MAIN = "main"
CONTENT_SHOP = "shop"
CONTENT_RADIO = "radio"
CONTENT_CROSS = "cross"
CONTENT_SITE = "site"
CONTENT_ROTATION = "rotation"


async def purge_main_catalog_woocommerce_urls() -> int:
    """Удаляет записи main с URL товаров WooCommerce (/product/). Возвращает число удалённых строк."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "DELETE FROM catalog WHERE content_type = ? AND INSTR(LOWER(url), '/product/') > 0",
                (CONTENT_MAIN,),
            )
            await db.commit()
            n = cursor.rowcount
        if n and n > 0:
            logger.info("[db] purge_main_catalog_woocommerce_urls: удалено %s строк", n)
        return int(n) if n is not None and n >= 0 else 0
    except Exception as e:
        logger.warning("[db] purge_main_catalog_woocommerce_urls: %s", e)
        return 0


async def init_db() -> None:
    """Создаёт таблицы при первом запуске."""
    logger.info("[db] init_db: путь=%s", DB_PATH)
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    excerpt TEXT,
                    category TEXT,
                    subcategory TEXT,
                    target_channel TEXT NOT NULL,
                    content_type TEXT DEFAULT 'main',
                    indexed_at INTEGER NOT NULL,
                    created_at DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS publication_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    channel_platform TEXT NOT NULL,
                    channel_name TEXT NOT NULL,
                    published_at INTEGER NOT NULL,
                    generated_text TEXT,
                    content_type TEXT NOT NULL,
                    created_at DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS rotation_state (
                    key TEXT PRIMARY KEY,
                    value_text TEXT,
                    value_int INTEGER,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            await db.execute("CREATE INDEX IF NOT EXISTS idx_catalog_target ON catalog(target_channel)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_catalog_content_type ON catalog(content_type)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_history_url ON publication_history(url)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_history_published ON publication_history(published_at)")
            await db.commit()
        logger.info("[db] init_db: таблицы созданы")
    except Exception as e:
        logger.exception("[db] init_db: ошибка — %s", e)
        raise


async def upsert_catalog_item(
    url: str,
    title: str,
    excerpt: str,
    category: str,
    subcategory: str,
    target_channel: str,
    content_type: str = CONTENT_MAIN,
) -> None:
    ts = int(time.time())
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO catalog (url, title, excerpt, category, subcategory, target_channel, content_type, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title=excluded.title,
                    excerpt=excluded.excerpt,
                    category=excluded.category,
                    subcategory=excluded.subcategory,
                    target_channel=excluded.target_channel,
                    content_type=excluded.content_type,
                    indexed_at=excluded.indexed_at
                """,
                (url, title, (excerpt or "")[:2000], category or "", subcategory or "", target_channel, content_type, ts),
            )
            await db.commit()
    except Exception as e:
        logger.exception("[db] upsert_catalog_item: %s — %s", url[:80], e)
        raise


async def get_catalog_for_channel(
    target_channel: str,
    exclude_urls_seen_after_ts: int | None = None,
    limit: int = 500,
    exclude_subcategory: str | None = None,
    order_by_random: bool = False,
    offset: int = 0,
) -> list[tuple[int, str, str, str, str]]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            query = "SELECT c.id, c.url, c.title, c.excerpt, c.subcategory FROM catalog c WHERE c.target_channel = ?"
            params: list[Any] = [target_channel]
            
            if exclude_urls_seen_after_ts is not None:
                query += " AND NOT EXISTS (SELECT 1 FROM publication_history h WHERE h.url = c.url AND h.published_at > ?)"
                params.append(exclude_urls_seen_after_ts)
                
            if exclude_subcategory:
                query += " AND (c.subcategory IS NULL OR c.subcategory != ?)"
                params.append(exclude_subcategory)
                
            if order_by_random:
                query += " ORDER BY RANDOM()"
            else:
                query += " ORDER BY c.id"
                
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
        return [tuple(r) for r in rows]
    except Exception as e:
        logger.exception("[db] get_catalog_for_channel: %s", e)
        raise


async def add_publication_history(
    url: str,
    channel_platform: str,
    channel_name: str,
    generated_text: str | None = None,
    content_type: str = CONTENT_MAIN,
) -> None:
    ts = int(time.time())
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO publication_history (url, channel_platform, channel_name, published_at, generated_text, content_type)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (url, channel_platform, channel_name, ts, (generated_text or "")[:5000], content_type),
            )
            await db.commit()
        logger.debug("[db] add_publication_history: url=%s platform=%s channel=%s", url[:50], channel_platform, channel_name)
    except Exception as e:
        logger.exception("[db] add_publication_history: %s", e)
        raise


async def get_last_ad_timestamp(content_type: str, channel_name: str) -> int | None:
    """Возвращает timestamp последней публикации данного типа рекламы в данном канале."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """
                SELECT MAX(published_at) FROM publication_history
                WHERE content_type = ? AND channel_name = ?
                """,
                (content_type, channel_name),
            )
            row = await cursor.fetchone()
        if row and row[0] is not None:
            return row[0]
        return None
    except Exception as e:
        logger.exception("[db] get_last_ad_timestamp: %s — %s", content_type, e)
        return None


async def get_last_publication_ts_for_url(url: str, content_type: str) -> int | None:
    """Возвращает timestamp последней публикации данного URL с данным content_type (для антидубля товаров)."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT MAX(published_at) FROM publication_history WHERE url = ? AND content_type = ?",
                (url, content_type),
            )
            row = await cursor.fetchone()
        if row and row[0] is not None:
            return row[0]
        return None
    except Exception as e:
        logger.exception("[db] get_last_publication_ts_for_url: %s", e)
        return None


async def get_rotation_state(key: str) -> str | int | None:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT value_text, value_int FROM rotation_state WHERE key = ?", (key,))
            row = await cursor.fetchone()
        if row is None:
            return None
        if row[0] is not None:
            return row[0]
        return row[1]
    except Exception as e:
        logger.exception("[db] get_rotation_state: %s — %s", key, e)
        return None


async def set_rotation_state(key: str, value_text: str | None = None, value_int: int | None = None) -> None:
    ts = int(time.time())
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO rotation_state (key, value_text, value_int, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value_text=excluded.value_text, value_int=excluded.value_int, updated_at=excluded.updated_at
                """,
                (key, value_text, value_int, ts),
            )
            await db.commit()
    except Exception as e:
        logger.exception("[db] set_rotation_state: %s — %s", key, e)
        raise
