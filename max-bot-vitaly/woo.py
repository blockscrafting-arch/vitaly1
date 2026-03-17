"""WooCommerce REST API v3: товары по разделам для рекламы магазина."""
import logging
from typing import Any

import httpx

from config import CHANNEL_DRINKS, CHANNEL_LIFHAKI, CHANNEL_TRAVEL, get_settings

logger = logging.getLogger(__name__)
SHOP_SECTION_TRAVEL = "travel"
SHOP_SECTION_DRINKS = "drinks"
SHOP_SECTION_DISHES = "lifhaki"


async def fetch_products(category_slug: str | None = None, per_page: int = 10) -> list[dict[str, Any]]:
    settings = get_settings()
    key = settings.woo_consumer_key.get_secret_value() if settings.woo_consumer_key else ""
    secret = settings.woo_consumer_secret.get_secret_value() if settings.woo_consumer_secret else ""
    if not key or not secret:
        logger.warning("[woo] WooCommerce ключи не заданы")
        return []
    url = f"{settings.woo_api_url}/products"
    params: dict[str, Any] = {"per_page": per_page}
    if category_slug:
        params["category"] = category_slug
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, params=params, auth=(key, secret))
            r.raise_for_status()
            data = r.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("[woo] fetch_products: %s", e)
        return []


def get_channel_for_shop_section(section: str) -> str:
    return {SHOP_SECTION_TRAVEL: CHANNEL_TRAVEL, SHOP_SECTION_DRINKS: CHANNEL_DRINKS, SHOP_SECTION_DISHES: CHANNEL_LIFHAKI}.get(section, CHANNEL_DRINKS)
