"""Тесты ai: generate_announcement (с моком httpx и config)."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock



@pytest.mark.asyncio
async def test_generate_announcement_empty_text(mock_env):
    """Пустой текст — None."""
    from ai import generate_announcement
    assert await generate_announcement("") is None
    assert await generate_announcement("   ") is None


@pytest.mark.asyncio
async def test_generate_announcement_no_api_key(mock_env):
    """Без API-ключа (пустой) — None."""
    from ai import generate_announcement
    with patch("ai.get_cached_settings_async", new_callable=AsyncMock, return_value={}):
        with patch("ai.get_settings") as m:
            mock_s = MagicMock()
            mock_s.openrouter_api_key.get_secret_value.return_value = ""
            m.return_value = mock_s
            assert await generate_announcement("Пост о кофе в Японии.") is None


@pytest.mark.asyncio
async def test_generate_announcement_success(mock_env):
    """Успешный ответ OpenRouter — dict с полями."""
    from ai import generate_announcement

    with patch("ai.get_cached_settings_async", new_callable=AsyncMock, return_value={}):
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.raise_for_status = MagicMock()
        fake_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"announce": "Анонс.", "benefit": "Польза.", "question": "Вопрос?", "topic": "Кофе", "country": "Япония", "rubric": "Напитки"}'
                    }
                }
            ]
        }
        with patch("ai.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=fake_response)
            result = await generate_announcement("Пост о кофе в Японии.")
    assert result is not None
    assert result["announce"] == "Анонс."
    assert result["benefit"] == "Польза."
    assert result["question"] == "Вопрос?"
    assert result["topic"] == "Кофе"
    assert result["country"] == "Япония"
    assert result["rubric"] == "Напитки"


@pytest.mark.asyncio
async def test_generate_announcement_json_with_backticks(mock_env):
    """Ответ в обёртке ```json ... ``` парсится."""
    from ai import generate_announcement

    with patch("ai.get_cached_settings_async", new_callable=AsyncMock, return_value={}):
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.raise_for_status = MagicMock()
        fake_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '```json\n{"announce": "A", "benefit": "B", "question": "C", "topic": "", "country": "", "rubric": ""}\n```'
                    }
                }
            ]
        }
        with patch("ai.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=fake_response)
            result = await generate_announcement("Текст поста.")
    assert result is not None
    assert result["announce"] == "A"
    assert result["question"] == "C"
