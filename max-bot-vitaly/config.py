"""Конфигурация бота из переменных окружения."""
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic.types import SecretStr


class Settings(BaseSettings):
    """Настройки приложения из .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MAX Bot (SecretStr — не попадает в repr/логи)
    max_bot_token: SecretStr = Field(..., description="Токен бота из @MasterBot")
    channel_id: str = Field(default="", description="ID канала MAX")
    group_chat_id: str = Field(default="", description="ID группы для анонсов")
    channel_url: str = Field(
        default="https://max.ru/id672301938557_biz",
        description="Публичная ссылка на канал",
    )
    bot_link_url: str = Field(default="", description="Ссылка на бота (для кнопки в группе)")

    # OpenRouter (SecretStr — не попадает в repr/логи)
    openrouter_api_key: SecretStr = Field(default="", description="API ключ OpenRouter")
    openrouter_model: str = Field(
        default="openai/gpt-4o-mini",
        description="Модель для генерации анонсов",
    )

    # Admin
    admin_user_id: int = Field(default=0, description="user_id администратора в MAX")
    test_group_chat_id: str = Field(default="", description="ID тестовой группы для /test")

    # Google Sheets
    google_credentials_path: str = Field(
        default="service_account.json",
        description="Путь к JSON ключу service account",
    )
    google_sheet_id: str = Field(default="", description="ID Google Таблицы")

    @property
    def google_credentials_file(self) -> Path:
        return Path(self.google_credentials_path)


def get_settings() -> Settings:
    """Возвращает загруженные настройки."""
    return Settings()
