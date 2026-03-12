"""Интеграция с Google Таблицей: настройки, тексты меню, история публикаций."""
import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from config import get_settings

logger = logging.getLogger(__name__)

# Кэш (обновляется при старте и по расписанию)
_cache: dict[str, Any] = {}
_cache_ts: float = 0
CACHE_TTL_SEC = 300  # 5 минут


def _resolve_credentials_path(raw_path: str | Path) -> Path | None:
    """
    Проверка пути к credentials: нормализация и ограничение в пределах проекта или CWD.
    Защита от path traversal, если значение пришло из ненадёжного источника.
    """
    raw = Path(raw_path)
    project_dir = Path(__file__).resolve().parent
    cwd = Path.cwd().resolve()
    if raw.is_absolute():
        path = raw.resolve()
    else:
        path = (project_dir / raw).resolve()
    if not path.exists():
        logger.warning("[sheets] _resolve_credentials_path: файл не найден: %s", path)
        return None
    try:
        path.resolve().relative_to(project_dir)
        logger.debug("[sheets] _resolve_credentials_path: путь в проекте, ok")
        return path
    except ValueError:
        pass
    try:
        path.resolve().relative_to(cwd)
        logger.debug("[sheets] _resolve_credentials_path: путь в CWD, ok")
        return path
    except ValueError:
        logger.warning("[sheets] google_credentials_path вне каталога проекта/CWD: %s", raw_path)
        return None


def _gc() -> Any:
    """Подключение gspread (ленивое, чтобы не падать без credentials)."""
    try:
        import gspread
        settings = get_settings()
        path = _resolve_credentials_path(settings.google_credentials_path)
        if not path:
            logger.warning("[sheets] _gc: путь к credentials не найден или не прошёл проверку")
            return None
        gc = gspread.service_account(filename=str(path))
        logger.info("[sheets] _gc: подключение по service_account успешно, path=%s", path)
        return gc
    except Exception as e:
        logger.warning("[sheets] _gc: Google Sheets недоступен — %s", e, exc_info=True)
        return None


def _sheet():
    """Открыть таблицу по ID из настроек."""
    gc = _gc()
    if not gc:
        return None
    settings = get_settings()
    if not settings.google_sheet_id:
        logger.debug("[sheets] _sheet: GOOGLE_SHEET_ID не задан")
        return None
    try:
        sh = gc.open_by_key(settings.google_sheet_id)
        logger.debug("[sheets] _sheet: таблица открыта по id=%s", settings.google_sheet_id[:8] + "...")
        return sh
    except Exception as e:
        logger.warning("[sheets] _sheet: не удалось открыть таблицу id=%s — %s", settings.google_sheet_id[:8] if settings.google_sheet_id else "", e)
        return None


def get_settings_from_sheet() -> dict[str, str]:
    """Читает лист «Настройки»: пары параметр — значение."""
    sh = _sheet()
    if not sh:
        logger.debug("[sheets] get_settings_from_sheet: таблица недоступна")
        return {}
    try:
        ws = sh.worksheet("Настройки")
        rows = ws.get_all_records()
        out = {r.get("Параметр", r.get("параметр", "")): r.get("Значение", r.get("значение", "")) for r in rows if r}
        logger.info("[sheets] get_settings_from_sheet: прочитано записей=%s", len(out))
        return out
    except Exception as e:
        logger.warning("[sheets] get_settings_from_sheet: %s", e, exc_info=True)
        return {}


def get_countries_from_sheet() -> list[tuple[str, bool]]:
    """Лист «Страны»: (страна, активна)."""
    sh = _sheet()
    if not sh:
        return []
    try:
        ws = sh.worksheet("Страны")
        rows = ws.get_all_records()
        out = [
            (str(r.get("Страна", r.get("страна", ""))), str(r.get("Активна", r.get("активна", ""))).strip().lower() == "да")
            for r in rows if r
        ]
        logger.debug("[sheets] get_countries_from_sheet: строк=%s", len(out))
        return out
    except Exception as e:
        logger.warning("[sheets] get_countries_from_sheet: %s", e, exc_info=True)
        return []


def get_topics_from_sheet() -> list[tuple[str, str, bool]]:
    """Лист «Темы»: (тема, рубрика, активна)."""
    sh = _sheet()
    if not sh:
        return []
    try:
        ws = sh.worksheet("Темы")
        rows = ws.get_all_records()
        out = [
            (
                str(r.get("Тема", r.get("тема", ""))),
                str(r.get("Рубрика", r.get("рубрика", ""))),
                str(r.get("Активна", r.get("активна", ""))).strip().lower() == "да",
            )
            for r in rows if r
        ]
        logger.debug("[sheets] get_topics_from_sheet: строк=%s", len(out))
        return out
    except Exception as e:
        logger.warning("[sheets] get_topics_from_sheet: %s", e, exc_info=True)
        return []


def get_rules_from_sheet() -> dict[str, bool]:
    """Лист «Правила»: правило — да/нет."""
    sh = _sheet()
    if not sh:
        return {}
    try:
        ws = sh.worksheet("Правила")
        rows = ws.get_all_records()
        key_col = "Правило" if rows and "Правило" in (rows[0] or {}) else "правило"
        val_col = "Значение" if rows and "Значение" in (rows[0] or {}) else "значение"
        out = {
            str(r.get(key_col, "")): str(r.get(val_col, "")).strip().lower() == "да"
            for r in rows if r
        }
        logger.debug("[sheets] get_rules_from_sheet: правил=%s, ключи=%s", len(out), list(out.keys()))
        return out
    except Exception as e:
        logger.warning("[sheets] get_rules_from_sheet: %s", e, exc_info=True)
        return {}


def get_menu_text_from_sheet(section: str, subsection: str | None, item: str | None) -> str | None:
    """Лист «Тексты меню»: по раздел/подраздел/item вернуть текст."""
    sh = _sheet()
    if not sh:
        return None
    try:
        ws = sh.worksheet("Тексты меню")
        rows = ws.get_all_records()
        for r in rows or []:
            s = str(r.get("раздел", r.get("Раздел", "")))
            sub = str(r.get("подраздел", r.get("Подраздел", "")))
            i = str(r.get("item", r.get("Item", r.get("item", ""))))
            if s == section and (subsection is None or sub == subsection) and (item is None or i == item):
                return str(r.get("текст", r.get("Текст", "")))
        return None
    except Exception as e:
        logger.warning("get_menu_text_from_sheet: %s", e)
        return None


def add_publication_to_sheet(date: str, topic: str, country: str, rubric: str, announce: str, question: str) -> None:
    """Добавить строку в лист «История»."""
    sh = _sheet()
    if not sh:
        logger.warning("[sheets] add_publication_to_sheet: таблица недоступна, запись пропущена")
        return
    try:
        ws = sh.worksheet("История")
        ws.append_row([date, topic, country, rubric, announce[:500], question[:300]])
        logger.info("[sheets] add_publication_to_sheet: строка добавлена в «История» date=%s topic=%s country=%s", date, topic, country)
    except Exception as e:
        logger.warning("[sheets] add_publication_to_sheet: %s", e, exc_info=True)


def refresh_cache() -> None:
    """Обновить кэш из таблицы."""
    global _cache_ts
    import time
    logger.info("[sheets] refresh_cache: начало обновления кэша")
    try:
        _cache["settings"] = get_settings_from_sheet()
        _cache["countries"] = get_countries_from_sheet()
        _cache["topics"] = get_topics_from_sheet()
        _cache["rules"] = get_rules_from_sheet()
        _cache_ts = time.time()
        logger.info("[sheets] refresh_cache: готово (settings=%s, countries=%s, topics=%s, rules=%s)",
                    len(_cache.get("settings") or {}), len(_cache.get("countries") or []),
                    len(_cache.get("topics") or []), len(_cache.get("rules") or {}))
    except Exception as e:
        logger.exception("[sheets] refresh_cache: ошибка — %s", e)
        raise


def get_cached_settings() -> dict[str, str]:
    """Настройки из кэша (или пустой dict)."""
    if not _cache or (time.time() - _cache_ts) > CACHE_TTL_SEC:
        refresh_cache()
    return _cache.get("settings") or {}


def get_cached_rules() -> dict[str, bool]:
    """Правила ротации из кэша (лист «Правила»: название правила → да/нет)."""
    if not _cache or (time.time() - _cache_ts) > CACHE_TTL_SEC:
        refresh_cache()
    return _cache.get("rules") or {}


async def refresh_cache_async() -> None:
    """Обновить кэш в потоке (для вызова из async без блокировки event loop)."""
    await asyncio.to_thread(refresh_cache)


async def get_cached_settings_async() -> dict[str, str]:
    """Настройки из кэша; при истечении TTL обновление в потоке."""
    if not _cache or (time.time() - _cache_ts) > CACHE_TTL_SEC:
        await refresh_cache_async()
    return _cache.get("settings") or {}


async def get_cached_rules_async() -> dict[str, bool]:
    """Правила из кэша; при истечении TTL обновление в потоке."""
    if not _cache or (time.time() - _cache_ts) > CACHE_TTL_SEC:
        await refresh_cache_async()
    return _cache.get("rules") or {}
