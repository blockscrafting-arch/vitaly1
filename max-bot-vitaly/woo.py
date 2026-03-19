"""WooCommerce REST API v3: товары по разделам для рекламы магазина."""
import asyncio
import logging
import re
from typing import Any

import aiosqlite
import httpx

from config import CHANNEL_DRINKS, CHANNEL_LIFHAKI, CHANNEL_TRAVEL, get_settings
from db import CONTENT_SHOP, DB_PATH, upsert_catalog_item

logger = logging.getLogger(__name__)
SHOP_SECTION_TRAVEL = "travel"
SHOP_SECTION_DRINKS = "drinks"
SHOP_SECTION_DISHES = "lifhaki"

# Маппинг: канал -> список slug/подстрок имени категории WooCommerce для сопоставления
CHANNEL_TO_WOO_CATEGORY_HINTS: dict[str, list[str]] = {
    CHANNEL_TRAVEL: ["putevoditel", "путеводител", "klassicheskij", "классическ"],
    CHANNEL_DRINKS: ["recepty-napitkov", "рецепт.*напитк", "napitk"],
    CHANNEL_LIFHAKI: ["recepty-blyud", "рецепт.*блюд", "blyud", "блюд"],
}
PER_PAGE = 20
BAD_REQUEST_CODES = (400, 404, 500, 502, 503, 504)


async def fetch_product_categories() -> list[dict[str, Any]]:
    """Загружает список категорий товаров WooCommerce."""
    settings = get_settings()
    key = settings.woo_consumer_key.get_secret_value() if settings.woo_consumer_key else ""
    secret = settings.woo_consumer_secret.get_secret_value() if settings.woo_consumer_secret else ""
    if not key or not secret:
        return []
    url = f"{settings.woo_api_url}/products/categories"
    result: list[dict[str, Any]] = []
    page = 1
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                r = await client.get(url, params={"per_page": 100, "page": page}, auth=(key, secret))
                if r.status_code in BAD_REQUEST_CODES and page > 1:
                    break
                r.raise_for_status()
                data = r.json()
                if not data:
                    break
                for item in data:
                    result.append({
                        "id": item.get("id"),
                        "name": (item.get("name") or "").strip(),
                        "slug": (item.get("slug") or "").strip(),
                    })
                if len(data) < 100:
                    break
                page += 1
                await asyncio.sleep(0.2)
    except Exception as e:
        logger.warning("[woo] fetch_product_categories: %s", e)
        return []
    logger.info("[woo] fetch_product_categories: загружено %s категорий", len(result))
    return result


def _match_channel_to_category(cat_name: str, cat_slug: str) -> str | None:
    """Определяет канал по имени/slug категории WooCommerce."""
    name_lower = cat_name.lower()
    slug_lower = cat_slug.lower()
    for channel, hints in CHANNEL_TO_WOO_CATEGORY_HINTS.items():
        for hint in hints:
            if hint in slug_lower or (re.search(hint, name_lower) if ".*" in hint else hint in name_lower):
                return channel
    return None


async def fetch_products(
    category_id: int | None = None,
    per_page: int = PER_PAGE,
    page: int = 1,
) -> list[dict[str, Any]]:
    """Загружает страницу товаров. category_id — ID категории WooCommerce."""
    settings = get_settings()
    key = settings.woo_consumer_key.get_secret_value() if settings.woo_consumer_key else ""
    secret = settings.woo_consumer_secret.get_secret_value() if settings.woo_consumer_secret else ""
    if not key or not secret:
        logger.warning("[woo] WooCommerce ключи не заданы")
        return []
    url = f"{settings.woo_api_url}/products"
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if category_id is not None:
        params["category"] = category_id
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, params=params, auth=(key, secret))
            if r.status_code in BAD_REQUEST_CODES and page > 1:
                return []
            r.raise_for_status()
            data = r.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("[woo] fetch_products: %s", e)
        return []


def get_channel_for_shop_section(section: str) -> str:
    return {
        SHOP_SECTION_TRAVEL: CHANNEL_TRAVEL,
        SHOP_SECTION_DRINKS: CHANNEL_DRINKS,
        SHOP_SECTION_DISHES: CHANNEL_LIFHAKI,
    }.get(section, CHANNEL_DRINKS)


async def index_shop_to_catalog() -> int:
    """
    Индексирует товары магазина в каталог (catalog) с content_type=shop.
    Возвращает количество добавленных/обновлённых записей.
    """
    categories = await fetch_product_categories()
    if not categories:
        return 0
    count = 0
    for cat in categories:
        channel = _match_channel_to_category(cat["name"], cat["slug"])
        if not channel:
            continue
        cat_id = cat.get("id")
        if not isinstance(cat_id, int):
            continue
        page = 1
        while page <= 10:
            products = await fetch_products(category_id=cat_id, per_page=PER_PAGE, page=page)
            if not products:
                break
            for prod in products:
                url = prod.get("permalink") or prod.get("link") or ""
                title = (prod.get("name") or "").strip()
                if not url or not title:
                    continue
                desc = (prod.get("short_description") or prod.get("description") or "")
                if "<" in str(desc):
                    desc = re.sub(r"<[^>]+>", "", str(desc)).strip()
                excerpt = (desc or "")[:2000]
                await upsert_catalog_item(
                    url=url,
                    title=title,
                    excerpt=excerpt,
                    category=cat.get("name") or "",
                    subcategory="",
                    target_channel=channel,
                    content_type=CONTENT_SHOP,
                )
                count += 1
            if len(products) < PER_PAGE:
                break
            page += 1
            await asyncio.sleep(0.2)
    logger.info("[woo] index_shop_to_catalog: обработано товаров %s", count)
    return count


async def get_shop_products_for_channel(
    channel: str,
    exclude_urls_seen_after_ts: int | None = None,
    limit: int = 100,
    order_by_random: bool = False,
) -> list[tuple[int, str, str, str, str]]:
    """
    Возвращает список товаров из каталога для канала (id, url, title, excerpt, subcategory).
    exclude_urls_seen_after_ts — не возвращать товары, опубликованные после этого timestamp.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            query = "SELECT c.id, c.url, c.title, c.excerpt, c.subcategory FROM catalog c WHERE c.target_channel = ? AND c.content_type = ?"
            params: list[Any] = [channel, CONTENT_SHOP]

            if exclude_urls_seen_after_ts is not None:
                query += " AND NOT EXISTS (SELECT 1 FROM publication_history h WHERE h.url = c.url AND h.content_type = ? AND h.published_at > ?)"
                params.extend([CONTENT_SHOP, exclude_urls_seen_after_ts])

            if order_by_random:
                query += " ORDER BY RANDOM()"
            else:
                query += " ORDER BY c.id"

            query += " LIMIT ?"
            params.append(limit)

            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
        return [tuple(r) for r in rows]
    except Exception as e:
        logger.exception("[woo] get_shop_products_for_channel: %s", e)
        return []
