"""Тесты handlers.menu_texts: parse_item_payload, get_menu_text."""
import pytest
from unittest.mock import patch

from handlers.menu_texts import MENU_TEXTS, get_menu_text, parse_item_payload


def test_parse_item_payload_valid():
    """Корректные item payload разбираются."""
    assert parse_item_payload("item:drinks:coffee:japan") == "drinks:coffee:japan"
    assert parse_item_payload("item:travel:route_3d") == "travel:route_3d"
    assert parse_item_payload("item:lifehack:pharmacy") == "lifehack:pharmacy"


def test_parse_item_payload_not_item():
    """Без префикса item: — None."""
    assert parse_item_payload("main") is None
    assert parse_item_payload("section:drinks") is None
    assert parse_item_payload("") is None


def test_get_menu_text_main_welcome():
    """Главное приветствие из MENU_TEXTS."""
    with patch("sheets.get_menu_text_from_sheet", return_value=None):
        text = get_menu_text("main_welcome")
    assert "Привет" in text
    assert "напитки" in text or "темам" in text


def test_get_menu_text_drinks_coffee_japan():
    """Текст по ключу drinks:coffee:japan."""
    with patch("sheets.get_menu_text_from_sheet", return_value=None):
        text = get_menu_text("drinks:coffee:japan")
    assert "Японии" in text or "кофе" in text
    assert text == MENU_TEXTS["drinks:coffee:japan"]


def test_get_menu_text_from_sheet_overrides():
    """Если таблица возвращает текст — используется он."""
    with patch("sheets.get_menu_text_from_sheet", return_value="Кастомный текст из таблицы"):
        text = get_menu_text("drinks:coffee:japan", section="drinks", subsection="coffee", item="japan")
    assert text == "Кастомный текст из таблицы"


def test_get_menu_text_unknown_key_fallback():
    """Неизвестный ключ — fallback с названием темы."""
    with patch("sheets.get_menu_text_from_sheet", return_value=None):
        text = get_menu_text("unknown:key")
    assert "unknown:key" in text
    assert "канале" in text or "Материалы" in text
