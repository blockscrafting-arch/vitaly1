"""Интеграция с Google Таблицей: настройки, тексты меню, история публикаций."""
import logging
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
        return None
    try:
        path.resolve().relative_to(project_dir)
        return path
    except ValueError:
        pass
    try:
        path.resolve().relative_to(cwd)
        return path
    except ValueError:
        logger.warning("google_credentials_path вне каталога проекта/CWD: %s", raw_path)
        return None


def _gc() -> Any:
    """Подключение gspread (ленивое, чтобы не падать без credentials)."""
    try:
        import gspread
        settings = get_settings()
        path = _resolve_credentials_path(settings.google_credentials_path)
        if not path:
            return None
        return gspread.service_account(filename=str(path))
    except Exception as e:
        logger.debug("Google Sheets недоступен: %s", e)
        return None


def _sheet():
    """Открыть таблицу по ID из настроек."""
    gc = _gc()
    if not gc:
        return None
    settings = get_settings()
    if not settings.google_sheet_id:
        return None
    try:
        return gc.open_by_key(settings.google_sheet_id)
    except Exception as e:
        logger.warning("Не удалось открыть Google Таблицу: %s", e)
        return None


def get_settings_from_sheet() -> dict[str, str]:
    """Читает лист «Настройки»: пары параметр — значение."""
    sh = _sheet()
    if not sh:
        return {}
    try:
        ws = sh.worksheet("Настройки")
        rows = ws.get_all_records()
        return {r.get("Параметр", r.get("параметр", "")): r.get("Значение", r.get("значение", "")) for r in rows if r}
    except Exception as e:
        logger.warning("get_settings_from_sheet: %s", e)
        return {}


def get_countries_from_sheet() -> list[tuple[str, bool]]:
    """Лист «Страны»: (страна, активна)."""
    sh = _sheet()
    if not sh:
        return []
    try:
        ws = sh.worksheet("Страны")
        rows = ws.get_all_records()
        return [
            (str(r.get("Страна", r.get("страна", ""))), str(r.get("Активна", r.get("активна", ""))).strip().lower() == "да")
            for r in rows if r
        ]
    except Exception as e:
        logger.warning("get_countries_from_sheet: %s", e)
        return []


def get_topics_from_sheet() -> list[tuple[str, str, bool]]:
    """Лист «Темы»: (тема, рубрика, активна)."""
    sh = _sheet()
    if not sh:
        return []
    try:
        ws = sh.worksheet("Темы")
        rows = ws.get_all_records()
        return [
            (
                str(r.get("Тема", r.get("тема", ""))),
                str(r.get("Рубрика", r.get("рубрика", ""))),
                str(r.get("Активна", r.get("активна", ""))).strip().lower() == "да",
            )
            for r in rows if r
        ]
    except Exception as e:
        logger.warning("get_topics_from_sheet: %s", e)
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
        return {
            str(r.get(key_col, "")): str(r.get(val_col, "")).strip().lower() == "да"
            for r in rows if r
        }
    except Exception as e:
        logger.warning("get_rules_from_sheet: %s", e)
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
        return
    try:
        ws = sh.worksheet("История")
        ws.append_row([date, topic, country, rubric, announce[:500], question[:300]])
    except Exception as e:
        logger.warning("add_publication_to_sheet: %s", e)


def refresh_cache() -> None:
    """Обновить кэш из таблицы."""
    global _cache_ts
    import time
    _cache["settings"] = get_settings_from_sheet()
    _cache["countries"] = get_countries_from_sheet()
    _cache["topics"] = get_topics_from_sheet()
    _cache["rules"] = get_rules_from_sheet()
    _cache_ts = time.time()


def get_cached_settings() -> dict[str, str]:
    """Настройки из кэша (или пустой dict)."""
    import time
    if not _cache or (time.time() - _cache_ts) > CACHE_TTL_SEC:
        refresh_cache()
    return _cache.get("settings") or {}
