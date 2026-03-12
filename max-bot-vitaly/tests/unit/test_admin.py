"""Тесты handlers.admin: is_autopost_paused, set_autopost_paused, _is_admin."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from handlers.admin import (
    PAUSE_FLAG_FILE,
    _is_admin,
    is_autopost_paused,
    set_autopost_paused,
)


def test_is_autopost_paused_and_set(monkeypatch, tmp_path):
    """Флаг паузы: изначально нет, после set(True) есть, после set(False) нет."""
    flag_file = tmp_path / ".autopost_paused"
    monkeypatch.setattr("handlers.admin.PAUSE_FLAG_FILE", flag_file)
    assert is_autopost_paused() is False
    set_autopost_paused(True)
    assert is_autopost_paused() is True
    set_autopost_paused(False)
    assert is_autopost_paused() is False


def test_is_admin_no_admin_user_id(monkeypatch, mock_env):
    """При admin_user_id=0 никто не админ."""
    with patch("handlers.admin.get_settings") as m:
        mock_s = MagicMock()
        mock_s.admin_user_id = 0
        m.return_value = mock_s
        event = MagicMock()
        event.message.sender.user_id = 123
        assert _is_admin(event) is False


def test_is_admin_match(monkeypatch, mock_env):
    """user_id совпадает с admin_user_id — админ."""
    with patch("handlers.admin.get_settings") as m:
        mock_s = MagicMock()
        mock_s.admin_user_id = 456
        m.return_value = mock_s
        event = MagicMock()
        event.message.sender.user_id = 456
        assert _is_admin(event) is True


def test_is_admin_no_match(monkeypatch, mock_env):
    """user_id не совпадает — не админ."""
    with patch("handlers.admin.get_settings") as m:
        mock_s = MagicMock()
        mock_s.admin_user_id = 456
        m.return_value = mock_s
        event = MagicMock()
        event.message.sender.user_id = 789
        assert _is_admin(event) is False


def test_is_admin_no_message_sender(monkeypatch, mock_env):
    """Нет message или sender — не админ."""
    with patch("handlers.admin.get_settings") as m:
        mock_s = MagicMock()
        mock_s.admin_user_id = 456
        m.return_value = mock_s
        event = MagicMock()
        event.message = None
        assert _is_admin(event) is False
