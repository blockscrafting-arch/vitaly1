"""Генерация анонсов постов через OpenRouter API."""
import json
import logging
from typing import Any

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — помощник для канала о напитках и путешествиях.
Тебе дают текст поста из канала. Твоя задача:
1. Написать короткий анонс (1-2 предложения — о чём пост)
2. Написать в чём польза для читателя (1-2 предложения)
3. Придумать вопрос для обсуждения в группе

Правила:
- Используй ТОЛЬКО факты из текста, ничего не придумывай
- Пиши кратко, живо, по-человечески
- Не используй восклицательные знаки, капслок, эмодзи
- Вопрос должен провоцировать делиться личным опытом

Ответ строго в JSON, один объект без markdown-обёртки:
{"announce": "...", "benefit": "...", "question": "..."}"""


async def generate_announcement(post_text: str) -> dict[str, str] | None:
    """
    Генерирует анонс, пользу и вопрос для обсуждения из текста поста.

    Returns:
        dict с ключами announce, benefit, question или None при ошибке.
    """
    if not post_text or not post_text.strip():
        logger.warning("generate_announcement: пустой post_text")
        return None

    settings = get_settings()
    api_key = settings.openrouter_api_key.get_secret_value() if settings.openrouter_api_key else ""
    if not api_key:
        logger.error("OPENROUTER_API_KEY не задан")
        return None

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://napitki133.ru",
    }
    payload: dict[str, Any] = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": post_text[:12000]},
        ],
        "temperature": 0.3,
        "max_tokens": 600,
    }

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            logger.warning("OpenRouter HTTP attempt %s: %s", attempt + 1, e)
            continue
        except Exception as e:
            logger.warning("OpenRouter attempt %s: %s", attempt + 1, e)
            continue

        choices = data.get("choices")
        if not choices or not isinstance(choices, list):
            logger.warning("OpenRouter: нет choices в ответе")
            continue

        content = choices[0].get("message", {}).get("content")
        if not content or not isinstance(content, str):
            logger.warning("OpenRouter: нет content в ответе")
            continue

        content = content.strip()
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
            logger.warning("OpenRouter: невалидный JSON (attempt %s): %s", attempt + 1, e)
            continue

        if not isinstance(parsed, dict):
            logger.warning("OpenRouter: ответ не объект")
            continue

        for key in ("announce", "benefit", "question"):
            if key not in parsed or not isinstance(parsed[key], str):
                logger.warning("OpenRouter: нет поля %s", key)
                break
        else:
            return {
                "announce": parsed["announce"].strip(),
                "benefit": parsed["benefit"].strip(),
                "question": parsed["question"].strip(),
            }
    logger.error("generate_announcement: не удалось получить валидный ответ после 3 попыток")
    return None
