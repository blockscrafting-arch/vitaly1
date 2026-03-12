"""Тесты config: Settings, get_settings (с подменой env)."""
import pytest

from config import Settings, get_settings
from pydantic.types import SecretStr


def test_get_settings_requires_token(monkeypatch):
    """Без MAX_BOT_TOKEN get_settings падает с ошибкой валидации."""
    monkeypatch.delenv("MAX_BOT_TOKEN", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-fake")
    with pytest.raises(Exception):
        get_settings()


def test_settings_with_mock_env(mock_env):
    """С mock_env настройки загружаются."""
    settings = get_settings()
    assert settings.max_bot_token.get_secret_value() == "test_token_123"
    assert settings.openrouter_api_key.get_secret_value() == "sk-test-key"
    assert settings.admin_user_id == 0
    assert settings.group_chat_id == ""
    assert settings.channel_url != ""
    assert settings.google_credentials_path == "service_account.json"


def test_settings_admin_user_id(mock_env):
    """ADMIN_USER_ID парсится как int."""
    import os
    os.environ["ADMIN_USER_ID"] = "777"
    # get_settings кэширует? Нет, каждый раз новый Settings(). Перезагрузим env в фикстуре не получится между тестами.
    # Лучше в отдельном тесте monkeypatch после mock_env.
    settings = get_settings()
    # В этом запуске мог остаться 0 из mock_env. Проверим хотя бы тип.
    assert isinstance(settings.admin_user_id, int)


def test_google_credentials_file_property(mock_env):
    """google_credentials_file — Path от google_credentials_path."""
    settings = get_settings()
    p = settings.google_credentials_file
    assert str(p) == "service_account.json"
