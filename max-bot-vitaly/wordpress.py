"""Индексация сайта napitki133.ru через WordPress REST API."""
import asyncio
import logging
import re
from typing import Any

import httpx

from config import CHANNEL_DRINKS, CHANNEL_LIFHAKI, CHANNEL_TRAVEL, get_settings

# Часть сайтов отдают 400 на page>1 при лимитах пагинации — не падаем, возвращаем что есть
BAD_REQUEST_CODES = (400, 404)
from db import upsert_catalog_item

logger = logging.getLogger(__name__)
PER_PAGE = 100


async def fetch_categories() -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.wp_api_url}/categories"
    result: list[dict[str, Any]] = []
    page = 1
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            r = await client.get(url, params={"per_page": PER_PAGE, "page": page})
            if r.status_code in BAD_REQUEST_CODES and page > 1:
                break
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            for item in data:
                result.append({"id": item.get("id"), "name": item.get("name", ""), "slug": item.get("slug", ""), "parent": item.get("parent", 0), "count": item.get("count", 0)})
            if len(data) < PER_PAGE:
                break
            page += 1
            await asyncio.sleep(0.2)
    logger.info("[wordpress] fetch_categories: загружено %s категорий", len(result))
    return result


async def fetch_posts_for_category(category_id: int) -> list[dict[str, Any]]:
    settings = get_settings()
    base = f"{settings.wp_api_url}/posts"
    result: list[dict[str, Any]] = []
    page = 1
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            r = await client.get(base, params={"categories": category_id, "per_page": PER_PAGE, "page": page})
            if r.status_code in BAD_REQUEST_CODES and page > 1:
                logger.debug("[wordpress] fetch_posts_for_category: category=%s page=%s %s, прекращаем пагинацию", category_id, page, r.status_code)
                break
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            for post in data:
                link = post.get("link", "")
                title = (post.get("title") or {}).get("rendered", "") or ""
                excerpt = (post.get("excerpt") or {}).get("rendered", "") or ""
                if "<" in excerpt:
                    excerpt = re.sub(r"<[^>]+>", "", excerpt).strip()[:1500]
                result.append({"url": link, "title": title, "excerpt": excerpt, "category_ids": post.get("categories") or []})
            if len(data) < PER_PAGE:
                break
            page += 1
            await asyncio.sleep(0.2)
    logger.info("[wordpress] fetch_posts_for_category: category=%s, постов=%s", category_id, len(result))
    return result


def default_category_to_channel() -> dict[str, str]:
    return {
        "travel": CHANNEL_TRAVEL, "путеводител": CHANNEL_TRAVEL, "тайланд": CHANNEL_TRAVEL, "библиотека": CHANNEL_TRAVEL,
        "lifhaki": CHANNEL_LIFHAKI, "лайфхак": CHANNEL_LIFHAKI,
        "drinks": CHANNEL_DRINKS, "напитк": CHANNEL_DRINKS, "виски": CHANNEL_DRINKS, "джин": CHANNEL_DRINKS, "ром": CHANNEL_DRINKS, "водка": CHANNEL_DRINKS, "вино": CHANNEL_DRINKS, "пиво": CHANNEL_DRINKS, "коктейл": CHANNEL_DRINKS, "кофе": CHANNEL_DRINKS, "чай": CHANNEL_DRINKS,
    }


def resolve_channel_for_categories(
    category_slugs: list[str],
    category_names: list[str],
    slug_to_channel: dict[str, str] | None = None,
) -> str | None:
    mapping = slug_to_channel or default_category_to_channel()
    combined = [(s, "slug") for s in (category_slugs or [])] + [(n, "name") for n in (category_names or [])]
    for value, _ in combined:
        val_lower = (value or "").lower()
        for pattern, channel in mapping.items():
            if pattern.lower() in val_lower or val_lower == pattern.lower():
                return channel
    return None


async def index_site_to_catalog(
    category_id_to_slugs: dict[int, list[str]] | None = None,
    slug_to_channel: dict[str, str] | None = None,
) -> int:
    categories = await fetch_categories()
    id_to_slug: dict[int, str] = {}
    id_to_name: dict[int, str] = {}
    for c in categories:
        id_to_slug[c["id"]] = c.get("slug", "")
        id_to_name[c["id"]] = c.get("name", "")
    total = 0
    seen_urls: set[str] = set()
    for cat in categories:
        cid = cat["id"]
        name = cat.get("name", "")
        if cat.get("count", 0) == 0:
            continue
        await asyncio.sleep(0.2)
        posts = await fetch_posts_for_category(cid)
        for post in posts:
            url = post.get("url", "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            cat_ids = post.get("category_ids", [])
            slugs = [id_to_slug.get(i, "") for i in cat_ids]
            names = [id_to_name.get(i, "") for i in cat_ids]
            channel = resolve_channel_for_categories(slugs, names, slug_to_channel=slug_to_channel)
            if not channel:
                continue
            subcategory = slugs[0] if slugs else ""
            await upsert_catalog_item(url=url, title=post.get("title", "")[:500], excerpt=post.get("excerpt", ""), category=name[:200], subcategory=subcategory[:200], target_channel=channel)
            total += 1
    logger.info("[wordpress] index_site_to_catalog: обработано записей: %s", total)
    return total
