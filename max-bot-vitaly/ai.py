"""Генерация анонсов постов через OpenRouter API."""
import json
import logging
from typing import Any

import httpx

from config import get_settings
from sheets import get_cached_settings_async

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """Ты — помощник для канала о напитках и путешествиях.
Тебе дают текст поста из канала. Твоя задача:
1. Написать короткий анонс (1-2 предложения — о чём пост)
2. Написать в чём польза для читателя (1-2 предложения)
3. Придумать вопрос для обсуждения в группе
4. Определить тему поста (одно короткое название, например "Локальный кофе", "Аптечка", "Районы для жизни") или пустую строку
5. Определить страну, если пост про конкретную страну (например "Япония", "Таиланд") или пустую строку
6. Определить рубрику: ровно одна из "Напитки", "Путешествия", "Лайфхаки", "Для удалёнки" или пустая строка

Правила:
- Используй ТОЛЬКО факты из текста, ничего не придумывай
- Пиши кратко, живо, по-человечески
- Не используй восклицательные знаки, капслок, эмодзи
- Вопрос должен провоцировать делиться личным опытом
- topic, country, rubric — только если явно следует из текста поста

Ответ строго в JSON, один объект без markdown-обёртки:
{"announce": "...", "benefit": "...", "question": "...", "topic": "...", "country": "...", "rubric": "..."}"""


def _get_system_prompt(settings_from_sheet: dict[str, str] | None = None) -> str:
    """Промпт для ИИ: из переданных настроек таблицы (ключ «Промпт для ИИ») или дефолтный."""
    try:
        settings = settings_from_sheet or {}
        prompt = (settings.get("Промпт для ИИ") or settings.get("Промпт ИИ") or "").strip()
        if prompt:
            logger.info("[ai] Промпт для ИИ взят из таблицы «Настройки», длина=%s", len(prompt))
            if "topic" not in prompt.lower() and "рубрик" not in prompt.lower():
                prompt += '\n\nОтвет в JSON: {"announce": "...", "benefit": "...", "question": "...", "topic": "...", "country": "...", "rubric": "..."}'
            return prompt
    except Exception as e:
        logger.warning("[ai] Промпт из таблицы недоступен, используем дефолт: %s", e, exc_info=True)
    logger.info("[ai] Используется дефолтный системный промпт")
    return DEFAULT_SYSTEM_PROMPT


async def generate_announcement(post_text: str) -> dict[str, Any] | None:
    """
    Генерирует анонс, пользу, вопрос и метаданные (topic, country, rubric) из текста поста.

    Returns:
        dict с ключами announce, benefit, question, topic, country, rubric или None при ошибке.
    """
    logger.info("[ai] generate_announcement: старт, post_text_len=%s", len(post_text or ""))
    if not post_text or not post_text.strip():
        logger.warning("[ai] generate_announcement: пустой post_text, выход")
        return None

    settings = get_settings()
    api_key = settings.openrouter_api_key.get_secret_value() if settings.openrouter_api_key else ""
    if not api_key:
        logger.error("[ai] OPENROUTER_API_KEY не задан в .env, выход")
        return None

    sheet_settings = await get_cached_settings_async()
    system_prompt = _get_system_prompt(sheet_settings)
    logger.info("[ai] Модель=%s, запрос к OpenRouter...", settings.openrouter_model)
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://napitki133.ru",
    }
    payload: dict[str, Any] = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": post_text[:12000]},
        ],
        "temperature": 0.3,
        "max_tokens": 600,
    }

    timeout = httpx.Timeout(60.0, connect=15.0)
    for attempt in range(3):
        try:
            logger.info("[ai] OpenRouter попытка %s/3: POST %s", attempt + 1, url)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            logger.info("[ai] OpenRouter ответ: status=%s, есть choices=%s", resp.status_code, bool(data.get("choices")))
        except httpx.TimeoutError as e:
            logger.warning("[ai] OpenRouter таймаут попытка %s/3: %s", attempt + 1, e)
            continue
        except httpx.HTTPError as e:
            logger.warning("[ai] OpenRouter HTTP попытка %s/3: %s (причина: %s)", attempt + 1, type(e).__name__, e)
            continue
        except Exception as e:
            logger.warning("[ai] OpenRouter попытка %s/3: %s — %s", attempt + 1, type(e).__name__, e, exc_info=True)
            continue

        choices = data.get("choices")
        if not choices or not isinstance(choices, list):
            logger.warning("[ai] OpenRouter: в ответе нет choices или не список, попытка %s", attempt + 1)
            continue

        content = choices[0].get("message", {}).get("content")
        if not content or not isinstance(content, str):
            logger.warning("[ai] OpenRouter: нет content в choices[0].message, попытка %s", attempt + 1)
            continue

        content = content.strip()
        logger.info("[ai] OpenRouter: content_len=%s, парсим JSON", len(content))
        # Убрать возможную обёртку ```json ... ```
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].lower().startswith("```json"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning("[ai] OpenRouter: невалидный JSON попытка %s: %s (фрагмент: %s)", attempt + 1, e, content[:200])
            continue

        if not isinstance(parsed, dict):
            logger.warning("[ai] OpenRouter: ответ не объект, тип=%s", type(parsed).__name__)
            continue

        for key in ("announce", "benefit", "question"):
            if key not in parsed or not isinstance(parsed[key], str):
                logger.warning("[ai] OpenRouter: нет или не строка поля %s в ответе, попытка %s", key, attempt + 1)
                break
        else:
            def _str(v: Any) -> str:
                return (v or "").strip() if isinstance(v, str) else ""

            result = {
                "announce": parsed["announce"].strip(),
                "benefit": parsed["benefit"].strip(),
                "question": parsed["question"].strip(),
                "topic": _str(parsed.get("topic")),
                "country": _str(parsed.get("country")),
                "rubric": _str(parsed.get("rubric")),
            }
            logger.info("[ai] generate_announcement: успех, topic=%r, country=%r, rubric=%r", result["topic"], result["country"], result["rubric"])
            return result
    logger.error("[ai] generate_announcement: не удалось получить валидный ответ после 3 попыток, выход")
    return None
