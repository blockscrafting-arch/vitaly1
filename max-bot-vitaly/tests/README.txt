Тесты бота MAX Vitaly
====================

Запуск (из каталога max-bot-vitaly, с активированным venv):

  pytest tests/ -v
  pytest tests/ -v --cov=. --cov-report=term-missing   # с отчётом покрытия

Зависимости для тестов: pytest, pytest-asyncio, pytest-cov (см. requirements-dev.txt).

Что покрыто
-----------
- utils.formatter: format_announce_message (все поля, пустые, лишние ключи).
- utils.anti_repeat: should_skip_by_antirepeat (пустая история, та же тема/страна, правила из таблицы).
- handlers.callbacks: _is_safe_payload (допустимые/недопустимые символы, длина).
- handlers.menu_texts: parse_item_payload, get_menu_text (таблица и fallback).
- handlers.admin: is_autopost_paused, set_autopost_paused, _is_admin.
- db: init_db, add_publication, get_last_publications, was_user_greeted, set_user_greeted.
- config: get_settings (обязательный токен, mock env).
- ai: generate_announcement (пустой текст, нет ключа, успешный ответ OpenRouter, JSON в backticks).
- sheets: _resolve_credentials_path (несуществующий файл, путь в проекте, путь снаружи).
- keyboards: наличие клавиатур (main_menu, drinks, coffee_countries, item_reply, announcement).

Для тестов handlers/keyboards используется мок maxapi в tests/conftest.py.
