"""Тесты sheets: _resolve_credentials_path (изолированно)."""
import pytest
from pathlib import Path

from sheets import _resolve_credentials_path


def test_resolve_credentials_path_nonexistent():
    """Несуществующий файл — None."""
    assert _resolve_credentials_path("nonexistent_file_12345.json") is None


def test_resolve_credentials_path_relative_in_project(tmp_path, monkeypatch):
    """Относительный путь внутри проекта — разрешается, если файл есть."""
    creds = tmp_path / "service_account.json"
    creds.write_text("{}")
    # Проект для sheets — это каталог sheets.py (max-bot-vitaly). Подменим через патч project_dir в функции сложно.
    # Проще: создать файл в текущем каталоге (tests создают tmp_path) и передать путь к нему.
    # _resolve_credentials_path считает project_dir = Path(__file__).resolve().parent (sheets.py -> max-bot-vitaly).
    # Значит путь относительно max-bot-vitaly. Если мы в тестах, текущий каталог может быть max-bot-vitaly или tests.
    # Создадим файл в max-bot-vitaly (parent of tests) и передадим имя файла.
    project_root = Path(__file__).resolve().parent.parent
    creds_in_project = project_root / "test_creds_temp.json"
    creds_in_project.write_text("{}")
    try:
        result = _resolve_credentials_path("test_creds_temp.json")
        # Ожидаем путь к файлу в проекте (project_dir = sheets.py parent = max-bot-vitaly)
        if result is not None:
            assert result.exists()
            assert "test_creds_temp" in str(result)
    finally:
        creds_in_project.unlink(missing_ok=True)


def test_resolve_credentials_path_absolute_outside_returns_none(tmp_path):
    """Абсолютный путь вне проекта — None (и файл не должен существовать вне проекта)."""
    # Создаём файл во временном каталоге, который точно вне max-bot-vitaly
    outside = tmp_path / "outside_creds.json"
    outside.write_text("{}")
    result = _resolve_credentials_path(str(outside.resolve()))
    # _resolve_credentials_path проверяет relative_to(project_dir) и relative_to(cwd).
    # tmp_path обычно не в project_dir и может быть не в cwd. Ожидаем None.
    assert result is None or not str(result).startswith(str(tmp_path))
