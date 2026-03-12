"""Тесты utils.anti_repeat (с моком db.get_last_publications)."""
import pytest
from unittest.mock import AsyncMock, patch

from utils.anti_repeat import should_skip_by_antirepeat


@pytest.mark.asyncio
async def test_should_skip_empty_history():
    """Пустая история — не пропускать."""
    with patch("utils.anti_repeat.get_last_publications", new_callable=AsyncMock, return_value=[]):
        assert await should_skip_by_antirepeat("Кофе", "Япония") is False


@pytest.mark.asyncio
async def test_should_skip_same_topic():
    """Та же тема подряд — пропускать."""
    with patch("utils.anti_repeat.get_last_publications", new_callable=AsyncMock, return_value=[("Локальный кофе", "Япония")]):
        assert await should_skip_by_antirepeat("Локальный кофе", "Таиланд") is True


@pytest.mark.asyncio
async def test_should_skip_same_country():
    """Та же страна подряд — пропускать."""
    with patch("utils.anti_repeat.get_last_publications", new_callable=AsyncMock, return_value=[("Чай", "Япония")]):
        assert await should_skip_by_antirepeat("Кофе", "Япония") is True


@pytest.mark.asyncio
async def test_should_skip_different_topic_and_country():
    """Другая тема и страна — не пропускать."""
    with patch("utils.anti_repeat.get_last_publications", new_callable=AsyncMock, return_value=[("Кофе", "Япония")]):
        assert await should_skip_by_antirepeat("Чай", "Таиланд") is False


@pytest.mark.asyncio
async def test_should_skip_topic_case_insensitive():
    """Сравнение темы без учёта регистра."""
    with patch("utils.anti_repeat.get_last_publications", new_callable=AsyncMock, return_value=[("локальный кофе", "Япония")]):
        assert await should_skip_by_antirepeat("Локальный кофе", "Таиланд") is True


@pytest.mark.asyncio
async def test_should_skip_rules_disabled():
    """Если в правилах оба антиповтора выключены — не пропускать."""
    rules = {
        "Не повторять тему подряд": False,
        "Не повторять страну подряд": False,
    }
    with patch("utils.anti_repeat.get_last_publications", new_callable=AsyncMock, return_value=[("Кофе", "Япония")]):
        assert await should_skip_by_antirepeat("Кофе", "Япония", rules=rules) is False


@pytest.mark.asyncio
async def test_should_skip_rules_topic_only():
    """Проверка только темы по правилам."""
    rules = {"Не повторять тему подряд": True, "Не повторять страну подряд": False}
    with patch("utils.anti_repeat.get_last_publications", new_callable=AsyncMock, return_value=[("Кофе", "Япония")]):
        assert await should_skip_by_antirepeat("Кофе", "Япония", rules=rules) is True
        assert await should_skip_by_antirepeat("Чай", "Япония", rules=rules) is False
