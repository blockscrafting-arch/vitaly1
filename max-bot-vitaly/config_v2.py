"""Конфигурация бота V2 (контент-машина) из переменных окружения."""
import logging
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic.types import SecretStr

logger = logging.getLogger(__name__)


# Имена каналов для маппинга (константы)
CHANNEL_TRAVEL = "travel"
CHANNEL_LIFHAKI = "lifhaki"
CHANNEL_DRINKS = "drinks"


class SettingsV2(BaseSettings):
    """Настройки V2 из .env. Префикс V2_ опционален для разделения с v1."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="V2_",
    )

    # Сайт
    wordpress_url: str = Field(
        default="https://napitki133.ru",
        description="Базовый URL сайта (WordPress)",
    )
    wordpress_api_path: str = Field(
        default="/wp-json/wp/v2",
        description="Путь к WordPress REST API",
    )

    # WooCommerce (опционально; если пусто — реклама магазина через fallback)
    woo_consumer_key: SecretStr = Field(default="", description="WooCommerce Consumer Key (ck_...)")
    woo_consumer_secret: SecretStr = Field(default="", description="WooCommerce Consumer Secret (cs_...)")
    woo_api_path: str = Field(default="/wp-json/wc/v3", description="Путь к WooCommerce API")

    # OpenRouter
    openrouter_api_key: SecretStr = Field(default="", description="API ключ OpenRouter")
    openrouter_model: str = Field(
        default="google/gemini-2.0-flash-001",
        description="Модель для генерации текстов",
    )

    # Telegram: один бот, 3 канала
    telegram_bot_token: SecretStr = Field(default="", description="Токен бота Telegram (@BotFather)")
    telegram_channel_travel: str = Field(default="", description="ID или @username канала Путешествия")
    telegram_channel_lifhaki: str = Field(default="", description="ID или @username канала Лайфхаки")
    telegram_channel_drinks: str = Field(default="", description="ID или @username канала Напитки")

    # MAX: один бот, 3 канала
    max_bot_token: SecretStr = Field(default="", description="Токен бота MAX (dev.max.ru)")
    max_channel_travel: str = Field(default="", description="ID канала MAX Путешествия")
    max_channel_lifhaki: str = Field(default="", description="ID канала MAX Лайфхаки")
    max_channel_drinks: str = Field(default="", description="ID канала MAX Напитки")

    # Ссылки для постов
    site_url: str = Field(default="https://napitki133.ru", description="Ссылка на сайт")
    radio_url: str = Field(
        default="https://napitki133.ru/internet-radio-sajta-napitki133-ru/",
        description="Ссылка на страницу плеера радио",
    )
    shop_url: str = Field(default="https://napitki133.ru/shop/", description="Ссылка на магазин")

    # Антидубли (дни)
    repeat_interval_days: int = Field(default=14, description="Не повторять материал раньше N дней")
    shop_repeat_days: int = Field(default=21, description="Не повторять товар раньше N дней")

    # Google Sheets (та же или отдельная таблица для V2)
    google_credentials_path: str = Field(default="service_account.json", description="Путь к JSON ключу")
    google_sheet_id: str = Field(default="", description="ID Google Таблицы V2 (маппинг, расписание, промпты)")

    @property
    def wp_api_url(self) -> str:
        return self.wordpress_url.rstrip("/") + self.wordpress_api_path

    @property
    def woo_api_url(self) -> str:
        return self.wordpress_url.rstrip("/") + self.woo_api_path

    def get_telegram_channel_ids(self) -> dict[str, str]:
        """Возвращает словарь channel_name -> id/username для Telegram."""
        return {
            CHANNEL_TRAVEL: self.telegram_channel_travel.strip(),
            CHANNEL_LIFHAKI: self.telegram_channel_lifhaki.strip(),
            CHANNEL_DRINKS: self.telegram_channel_drinks.strip(),
        }

    def get_max_channel_ids(self) -> dict[str, str]:
        """Возвращает словарь channel_name -> id для MAX."""
        return {
            CHANNEL_TRAVEL: self.max_channel_travel.strip(),
            CHANNEL_LIFHAKI: self.max_channel_lifhaki.strip(),
            CHANNEL_DRINKS: self.max_channel_drinks.strip(),
        }


def get_settings_v2() -> SettingsV2:
    """Возвращает настройки V2."""
    try:
        return SettingsV2()
    except Exception as e:
        logger.exception("[config_v2] get_settings_v2: ошибка загрузки .env — %s", e)
        raise
