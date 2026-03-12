"""Тесты handlers.callbacks: _is_safe_payload."""
import pytest

from handlers.callbacks import _is_safe_payload


def test_safe_payload_valid():
    """Допустимые payload проходят."""
    assert _is_safe_payload("main") is True
    assert _is_safe_payload("start_menu") is True
    assert _is_safe_payload("section:drinks") is True
    assert _is_safe_payload("item:drinks:coffee:japan") is True
    assert _is_safe_payload("sub:drinks:coffee") is True
    assert _is_safe_payload("A-Z_a-z_0-9.-:") is True


def test_safe_payload_empty():
    """Пустая строка — небезопасно."""
    assert _is_safe_payload("") is False
    assert _is_safe_payload("   ") is False


def test_safe_payload_too_long():
    """Длина > 256 — небезопасно."""
    assert _is_safe_payload("a" * 257) is False
    assert _is_safe_payload("a" * 256) is True


def test_safe_payload_forbidden_chars():
    """Запрещённые символы — небезопасно."""
    assert _is_safe_payload("main/evil") is False
    assert _is_safe_payload("item:../../etc/passwd") is False
    assert _is_safe_payload("section;drop") is False
    assert _is_safe_payload("a b") is False
    assert _is_safe_payload("привет") is False
