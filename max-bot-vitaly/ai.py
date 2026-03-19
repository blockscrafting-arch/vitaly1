"""Генерация короткого поста через OpenRouter (по каналу и типу контента)."""
import logging
import re
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
# Промпты site promo по каналам (ТЗ v3.0, раздел 9.4)
PROMPTS_SITE = {
    CHANNEL_TRAVEL: """Ты — редактор. Напиши мягкий пост про napitki133.ru с акцентом на путеводители, маршруты, города и подборки мест.
Упомяни конкретные разделы или типы материалов. 2-3 предложения. Ссылку не пиши. Без восклицаний.""",
    CHANNEL_LIFHAKI: """Ты — редактор. Напиши мягкий пост про napitki133.ru с акцентом на практическую пользу, полезные инструкции и подборки решений.
Упомяни конкретные разделы или типы материалов. 2-3 предложения. Ссылку не пиши. Без восклицаний.""",
    CHANNEL_DRINKS: """Ты — редактор. Напиши мягкий пост про napitki133.ru с акцентом на рецепты напитков, стили, вкусы и подборки.
Упомяни конкретные разделы или типы материалов. 2-3 предложения. Ссылку не пиши. Без восклицаний.""",
}

# Промпты AV ротации по каналам (ТЗ v3.0, раздел 8.7)
PROMPTS_ROTATION = {
    CHANNEL_TRAVEL: """Ты — редактор канала о путешествиях. По аудио/видео материалу напиши короткий пост (2-3 предложения).
Структура: место, атмосфера, маршрут или впечатление, зачем послушать или посмотреть перед поездкой.
Правила: без восклицаний, капслока и эмодзи. Только текст, без markdown.""",
    CHANNEL_LIFHAKI: """Ты — редактор канала про лайфхаки. По аудио/видео материалу напиши короткий пост (2-3 предложения).
Структура: польза, короткая практическая мысль, зачем посмотреть или послушать и взять себе.
Правила: без восклицаний и капслока. Только текст.""",
    CHANNEL_DRINKS: """Ты — редактор канала о напитках. По аудио/видео материалу напиши короткий пост (2-3 предложения).
Структура: напиток, вкус, настроение, зачем включить или посмотреть.
Правила: без восклицаний и капслока. Только текст.""",
}


def _get_system_prompt(channel: str, content_type: str) -> str:
    """Промпт из Google Таблицы (лист Промпты) или хардкод."""
    try:
        from sheets import get_prompts_from_sheet
        prompts = get_prompts_from_sheet()
        if prompts:
            if content_type == "main":
                key = f"main_{channel}"
                if key in prompts and prompts[key].strip():
                    return prompts[key].strip()
            elif content_type == "rotation":
                key = f"rotation_{channel}"
                if key in prompts and prompts[key].strip():
                    return prompts[key].strip()
            elif content_type == "site":
                key = f"site_{channel}"
                if key in prompts and prompts[key].strip():
                    return prompts[key].strip()
            else:
                key = content_type
                if key in prompts and prompts[key].strip():
                    return prompts[key].strip()
    except Exception:
        pass
    if content_type == "main":
        return PROMPTS_MAIN.get(channel, PROMPTS_MAIN[CHANNEL_DRINKS])
    if content_type == "rotation":
        return PROMPTS_ROTATION.get(channel, PROMPTS_ROTATION[CHANNEL_DRINKS])
    if content_type == "shop":
        return PROMPT_SHOP
    if content_type == "radio":
        return PROMPT_RADIO
    if content_type == "cross":
        return PROMPT_CROSS
    if content_type == "site":
        return PROMPTS_SITE.get(channel, PROMPTS_SITE[CHANNEL_DRINKS])
    return PROMPTS_MAIN.get(channel, PROMPTS_MAIN[CHANNEL_DRINKS])


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
    system = _get_system_prompt(channel, content_type)
    user_content = f"Заголовок: {title}\n\nФрагмент: {(excerpt or '')[:2000]}{extra_context}"
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


def fallback_text(title: str, url: str, excerpt: str = "") -> str:
    """Fallback при недоступности OpenRouter: заголовок + первые 2 предложения + ссылка."""
    parts = [title]
    if excerpt:
        sentences = re.split(r"(?<=[.!?])\s+", excerpt.strip())
        preview = " ".join(sentences[:2])
        if preview:
            parts.append(preview)
    if url:
        parts.append(url)
    return "\n\n".join(parts)
