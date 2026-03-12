"""Логика антиповтора: не повторять тему/страну подряд по правилам из таблицы."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from db import get_last_publications

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Варианты названий правил в листе «Правила» (да/нет)
_RULE_TOPIC_KEYS = ("Не повторять тему подряд", "Не повторять одну тему два поста подряд")
_RULE_COUNTRY_KEYS = ("Не повторять страну подряд", "Не повторять одну страну два поста подряд")


def _rule_enabled(rules: dict[str, bool], keys: tuple[str, ...]) -> bool:
    """True если хотя бы один ключ есть в rules и значение True («да»)."""
    for k in keys:
        if rules.get(k):
            return True
    return False


def _rule_mentioned(rules: dict[str, bool], keys: tuple[str, ...]) -> bool:
    """Есть ли в rules хотя бы один из ключей (чтобы не считать «включённым по умолчанию»)."""
    return any(k in rules for k in keys)


async def should_skip_by_antirepeat(
    topic: str | None,
    country: str | None,
    last_n: int = 10,
    rules: dict[str, bool] | None = None,
) -> bool:
    """
    Возвращает True, если по правилам антиповтора эту публикацию лучше пропустить
    (та же тема или та же страна что в последней записи).

    rules: из листа «Правила» (название → True если «да»). Если правил нет в таблице — оба считаются включёнными.
    """
    rules = rules or {}
    check_topic = _rule_enabled(rules, _RULE_TOPIC_KEYS) if _rule_mentioned(rules, _RULE_TOPIC_KEYS) else True
    check_country = _rule_enabled(rules, _RULE_COUNTRY_KEYS) if _rule_mentioned(rules, _RULE_COUNTRY_KEYS) else True
    logger.debug("[anti_repeat] should_skip: topic=%r country=%r check_topic=%s check_country=%s", topic, country, check_topic, check_country)
    if not check_topic and not check_country:
        return False

    last = await get_last_publications(limit=last_n)
    if not last:
        logger.debug("[anti_repeat] should_skip: история пуста, не пропускаем")
        return False
    last_topic, last_country = last[0]
    if check_topic and topic and last_topic and topic.strip().lower() == last_topic.strip().lower():
        logger.info("[anti_repeat] should_skip: пропуск — та же тема подряд: %r", topic)
        return True
    if check_country and country and last_country and country.strip().lower() == last_country.strip().lower():
        logger.info("[anti_repeat] should_skip: пропуск — та же страна подряд: %r", country)
        return True
    logger.debug("[anti_repeat] should_skip: не пропускаем (last_topic=%r last_country=%r)", last_topic, last_country)
    return False
