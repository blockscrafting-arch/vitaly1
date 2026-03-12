"""Общие фикстуры и настройка путей для тестов."""
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Корень проекта (max-bot-vitaly) в PYTHONPATH для импорта config, db, utils и т.д.
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Мок maxapi для тестов, которые импортируют handlers/keyboards (подмодули должны быть в sys.modules)
def _ensure_maxapi_mock():
    if "maxapi.filters" in sys.modules and getattr(sys.modules["maxapi.filters"], "Command", None) is not None:
        return
    mx = types.ModuleType("maxapi")
    mx.__path__ = []
    mf = types.ModuleType("maxapi.filters")
    mf.Command = MagicMock()
    mt = types.ModuleType("maxapi.types")
    for name in ("MessageCreated", "MessageCallback", "BotStarted", "UserAdded", "CallbackButton", "LinkButton"):
        setattr(mt, name, MagicMock())
    mtu = types.ModuleType("maxapi.types.updates")
    mtuc = types.ModuleType("maxapi.types.updates.message_callback")
    mtuc.MessageForCallback = MagicMock()
    mtu.message_callback = mtuc
    mt.updates = mtu
    mx.filters = mf
    mx.types = mt
    mu = types.ModuleType("maxapi.utils")
    mui = types.ModuleType("maxapi.utils.inline_keyboard")
    mui.InlineKeyboardBuilder = MagicMock()
    mu.inline_keyboard = mui
    mx.utils = mu
    sys.modules["maxapi"] = mx
    sys.modules["maxapi.filters"] = mf
    sys.modules["maxapi.types"] = mt
    sys.modules["maxapi.types.updates"] = mtu
    sys.modules["maxapi.types.updates.message_callback"] = mtuc
    sys.modules["maxapi.utils"] = mu
    sys.modules["maxapi.utils.inline_keyboard"] = mui

_ensure_maxapi_mock()


@pytest.fixture
def db_path(tmp_path):
    """Временный путь к SQLite для тестов БД."""
    return tmp_path / "test.db"


@pytest.fixture
async def db_with_path(monkeypatch, db_path):
    """Подменить DB_PATH и инициализировать БД. Использовать в тестах db."""
    import db
    monkeypatch.setattr(db, "DB_PATH", db_path)
    await db.init_db()
    yield db
    # Очистка не обязательна для tmp_path


@pytest.fixture
def mock_env(monkeypatch):
    """Минимальный .env для тестов (токен обязателен для Settings)."""
    monkeypatch.setenv("MAX_BOT_TOKEN", "test_token_123")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-key")
    monkeypatch.setenv("ADMIN_USER_ID", "0")
    monkeypatch.setenv("GROUP_CHAT_ID", "")
    monkeypatch.setenv("CHANNEL_ID", "")
    monkeypatch.setenv("GOOGLE_SHEET_ID", "")
    monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", "service_account.json")
