"""WooCommerce REST API v3: товары по разделам для рекламы магазина (режим Б)."""
import logging
from typing import Any

import httpx

from config_v2 import CHANNEL_DRINKS, CHANNEL_LIFHAKI, CHANNEL_TRAVEL, get_settings_v2

logger = logging.getLogger(__name__)

# Разделы магазина → канал (по ТЗ)
SHOP_SECTION_TRAVEL = "travel"  # Классический путеводитель → Путешествия
SHOP_SECTION_DRINKS = "drinks"  # Рецепты напитков → Напитки
SHOP_SECTION_DISHES = "lifhaki"  # Рецепты блюд → Лайфхаки


async def fetch_products(category_slug: str | None = None, per_page: int = 10) -> list[dict[str, Any]]:
    """
    Загружает товары. category_slug — slug категории WooCommerce (опционально).
    Требует V2_WOO_CONSUMER_KEY и V2_WOO_CONSUMER_SECRET.
    """
    settings = get_settings_v2()
    key = settings.woo_consumer_key.get_secret_value() if settings.woo_consumer_key else ""
    secret = settings.woo_consumer_secret.get_secret_value() if settings.woo_consumer_secret else ""
    if not key or not secret:
        logger.warning("[woo_v2] WooCommerce ключи не заданы")
        return []
    url = f"{settings.woo_api_url}/products"
    params: dict[str, Any] = {"per_page": per_page}
    if category_slug:
        # Сначала получить ID категории по slug (отдельный запрос) или передать category id
        params["category"] = category_slug  # WC API может принимать slug в части реализаций
    auth = (key, secret)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, params=params, auth=auth)
            r.raise_for_status()
            data = r.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("[woo_v2] fetch_products: %s", e)
        return []


def get_channel_for_shop_section(section: str) -> str:
    """Возвращает канал для раздела магазина (travel/drinks/lifhaki)."""
    return {
        SHOP_SECTION_TRAVEL: CHANNEL_TRAVEL,
        SHOP_SECTION_DRINKS: CHANNEL_DRINKS,
        SHOP_SECTION_DISHES: CHANNEL_LIFHAKI,
    }.get(section, CHANNEL_DRINKS)
