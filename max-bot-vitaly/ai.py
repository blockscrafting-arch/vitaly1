"""Генерация короткого поста через OpenRouter (по каналу и типу контента)."""
import logging
from typing import Any

import httpx

from config import CHANNEL_DRINKS, CHANNEL_LIFHAKI, CHANNEL_TRAVEL, get_settings

logger = logging.getLogger(__name__)

PROMPTS_MAIN = {
    CHANNEL_TRAVEL: """Ты — редактор канала о путешествиях. По материалу с сайта напиши короткий пост для соцсети (2–4 предложения).
Структура: сильный заход про место, короткий факт/маршрут/сценарий, зачем открыть материал. В конце — призыв перейти по ссылке (ссылку не пиши, её подставят).
Правила: без восклицаний, капслока и нагромождения эмодзи. Только текст, без markdown.""",
    CHANNEL_LIFHAKI: """Ты — редактор канала про лайфхаки. По материалу с сайта напиши короткий пост (2–4 предложения).
Структура: ошибка/ловушка/польза, решение, зачем открыть. В конце — призыв перейти по ссылке (ссылку не пиши).
Правила: без восклицаний и капслока. Только текст.""",
    CHANNEL_DRINKS: """Ты — редактор канала о напитках. По материалу с сайта напиши короткий пост (2–4 предложения).
Структура: вкус/стиль/напиток, один факт или образ, зачем открыть. В конце — призыв перейти по ссылке (ссылку не пиши).
Правила: без восклицаний и капслока. Только текст.""",
}
PROMPT_SHOP = """Ты — редактор. Опиши книгу/материал из магазина: что это, кому пригодится, чем полезно. 2–4 предложения. В конце — призыв перейти в магазин (ссылку не пиши). Без восклицаний и капслока."""
PROMPT_RADIO = """Ты — редактор. Напиши короткий атмосферный пост про радио сайта: настроение (вечер, дорога, работа, кофе, дождь — выбери одно), когда включить, зачем перейти. 2–3 предложения. Ссылку не пиши. Без восклицаний."""
PROMPT_CROSS = """Ты — редактор. Напиши нативный анонс другого канала для подписчиков: кому зайдёт, почему стоит перейти. Без слов «подпишитесь» и без восклицаний. 2–3 предложения."""
PROMPT_SITE = """Ты — редактор. Напиши мягкий пост про сайт napitki133.ru в целом: что там найдёшь, зачем зайти. 2–3 предложения. Ссылку не пиши. Без восклицаний."""


async def generate_post(
    channel: str,
    content_type: str,
    title: str,
    excerpt: str,
    url: str,
    extra_context: str = "",
) -> str | None:
    settings = get_settings()
    api_key = settings.openrouter_api_key.get_secret_value() if settings.openrouter_api_key else ""
    if not api_key:
        logger.error("[ai] OPENROUTER_API_KEY не задан")
        return None
    if content_type == "main":
        system = PROMPTS_MAIN.get(channel, PROMPTS_MAIN[CHANNEL_DRINKS])
    elif content_type == "shop":
        system = PROMPT_SHOP
    elif content_type == "radio":
        system = PROMPT_RADIO
    elif content_type == "cross":
        system = PROMPT_CROSS
    elif content_type == "site":
        system = PROMPT_SITE
    else:
        system = PROMPTS_MAIN.get(channel, PROMPTS_MAIN[CHANNEL_DRINKS])
    user_content = f"Заголовок: {title}\n\nФрагмент: {excerpt[:2000]}{extra_context}"
    if url:
        user_content += f"\n\nСсылка на материал (в пост не вставлять): {url}"
    payload: dict[str, Any] = {
        "model": settings.openrouter_model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_content}],
        "temperature": 0.4,
        "max_tokens": 400,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "HTTP-Referer": "https://napitki133.ru"}
    timeout = httpx.Timeout(60.0, connect=15.0)
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            choices = data.get("choices")
            if not choices or not isinstance(choices, list):
                continue
            content = (choices[0].get("message") or {}).get("content")
            if content and isinstance(content, str):
                text = content.strip()
                if text:
                    logger.info("[ai] generate_post: успех, channel=%s type=%s len=%s", channel, content_type, len(text))
                    return text
        except Exception as e:
            logger.warning("[ai] OpenRouter попытка %s/3: %s", attempt + 1, e)
    logger.error("[ai] generate_post: не удалось после 3 попыток")
    return None


def fallback_text(title: str, url: str) -> str:
    return f"{title}\n\n{url}"
