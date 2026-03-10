"""Форматирование сообщений для группы."""
from typing import Any


def format_announce_message(data: dict[str, str]) -> str:
    """
    Формирует текст сообщения для группы из результата ИИ.

    Args:
        data: dict с ключами announce, benefit, question

    Returns:
        Текст в формате для отправки (markdown не обязателен, простые переносы).
    """
    announce = data.get("announce", "").strip()
    benefit = data.get("benefit", "").strip()
    question = data.get("question", "").strip()
    parts = [announce, benefit, question]
    return "\n\n".join(p for p in parts if p)
