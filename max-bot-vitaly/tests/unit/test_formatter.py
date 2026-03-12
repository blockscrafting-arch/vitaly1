"""Тесты utils.formatter."""
import pytest

from utils.formatter import format_announce_message


def test_format_announce_message_full():
    """Все три поля заполнены — склеиваются через двойной перенос."""
    data = {
        "announce": "Короткий анонс.",
        "benefit": "Польза для читателя.",
        "question": "Вопрос для обсуждения?",
    }
    assert format_announce_message(data) == "Короткий анонс.\n\nПольза для читателя.\n\nВопрос для обсуждения?"


def test_format_announce_message_partial():
    """Только announce и question — пустые части не попадают в вывод."""
    data = {"announce": "Анонс", "benefit": "", "question": "Вопрос?"}
    assert format_announce_message(data) == "Анонс\n\nВопрос?"


def test_format_announce_message_empty_parts_stripped():
    """Пробельные части отбрасываются."""
    data = {"announce": "  Анонс  ", "benefit": "   ", "question": "Вопрос"}
    assert format_announce_message(data) == "Анонс\n\nВопрос"


def test_format_announce_message_empty_dict():
    """Пустой dict — пустая строка."""
    assert format_announce_message({}) == ""


def test_format_announce_message_extra_keys_ignored():
    """Доп. ключи (topic, country) не ломают вывод."""
    data = {
        "announce": "А",
        "benefit": "B",
        "question": "C",
        "topic": "Кофе",
        "country": "Япония",
    }
    assert format_announce_message(data) == "А\n\nB\n\nC"


def test_format_announce_message_missing_keys():
    """Отсутствующие ключи дают пустые строки."""
    data = {"announce": "Только анонс"}
    assert format_announce_message(data) == "Только анонс"
