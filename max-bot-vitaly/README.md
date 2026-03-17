# Контент-машина napitki133.ru

Один бот: индексация сайта (WordPress REST API), выборка по кругу/вразнобой, генерация текста (OpenRouter), публикация в 3 канала Telegram и 3 канала MAX по расписанию (МСК).

## Запуск

```bash
cp .env.example .env
# заполнить переменные с префиксом V2_ в .env
python bot.py
```

## Требования

- Python 3.10+
- Переменные окружения с префиксом `V2_` (см. `.env.example`)

## Документация

- **Деплой на VPS:** [DEPLOY_VPS.md](DEPLOY_VPS.md)
- **После git pull:** [AFTER_GIT_PULL.md](AFTER_GIT_PULL.md)

## Структура

- `bot.py` — точка входа, инициализация БД и планировщика
- `config.py` — настройки из `.env` (префикс `V2_`)
- `db.py` — SQLite: каталог, история публикаций, ротация
- `wordpress.py` — индексация сайта
- `router.py` — выбор следующего материала для канала
- `ai.py` — генерация поста через OpenRouter
- `publishers.py` — публикация в Telegram и MAX
- `jobs.py` — задачи: основной пост, индексация
- `scheduler.py` — APScheduler, слоты по расписанию
- `sheets.py` — Google Таблица (маппинг, история)
- `woo.py` — заготовка WooCommerce
