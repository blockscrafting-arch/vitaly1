"""Тесты db: init_db, add_publication, get_last_publications, greeted."""
import pytest

import db


@pytest.mark.asyncio
async def test_init_db_and_add_publication(db_with_path):
    """Инициализация и запись публикации."""
    await db.add_publication(
        timestamp=1000,
        announce_text="Тест анонс",
        topic="Кофе",
        country="Япония",
    )
    last = await db.get_last_publications(limit=5)
    assert len(last) == 1
    assert last[0] == ("Кофе", "Япония")


@pytest.mark.asyncio
async def test_get_last_publications_order(db_with_path):
    """Последние записи в порядке убывания id."""
    await db.add_publication(1000, announce_text="1", topic="A", country="X")
    await db.add_publication(1001, announce_text="2", topic="B", country="Y")
    await db.add_publication(1002, announce_text="3", topic="C", country="Z")
    last = await db.get_last_publications(limit=10)
    assert last[0] == ("C", "Z")
    assert last[1] == ("B", "Y")
    assert last[2] == ("A", "X")


@pytest.mark.asyncio
async def test_get_last_publications_limit(db_with_path):
    """Лимит ограничивает количество записей."""
    for i in range(5):
        await db.add_publication(1000 + i, topic=f"T{i}", country=f"C{i}")
    last = await db.get_last_publications(limit=2)
    assert len(last) == 2


@pytest.mark.asyncio
async def test_was_user_greeted_false(db_with_path):
    """Новый пользователь — ещё не приветствован."""
    assert await db.was_user_greeted(99999) is False


@pytest.mark.asyncio
async def test_set_and_was_user_greeted(db_with_path):
    """После set_user_greeted was_user_greeted возвращает True."""
    await db.set_user_greeted(12345, chat_id=100)
    assert await db.was_user_greeted(12345) is True
    assert await db.was_user_greeted(99999) is False


@pytest.mark.asyncio
async def test_set_user_greeted_replace(db_with_path):
    """Повторный set_user_greeted обновляет запись (INSERT OR REPLACE)."""
    await db.set_user_greeted(111, chat_id=1)
    await db.set_user_greeted(111, chat_id=2)
    assert await db.was_user_greeted(111) is True
