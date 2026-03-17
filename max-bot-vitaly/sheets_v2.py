"""Google Таблица для V2: маппинг категорий, расписание, промпты (опционально)."""
import logging
from pathlib import Path
from typing import Any

from config_v2 import CHANNEL_DRINKS, CHANNEL_LIFHAKI, CHANNEL_TRAVEL, get_settings_v2

logger = logging.getLogger(__name__)

# Нормализация названия канала из таблицы -> внутренний ключ
SHEET_CHANNEL_TO_KEY = {
    "travel": CHANNEL_TRAVEL,
    "путешествия": CHANNEL_TRAVEL,
    "drinks": CHANNEL_DRINKS,
    "напитки": CHANNEL_DRINKS,
    "lifhaki": CHANNEL_LIFHAKI,
    "лайфхаки": CHANNEL_LIFHAKI,
}


def _resolve_credentials_path_v2(raw_path: str | Path) -> Path | None:
    """
    Проверка пути к credentials: нормализация и ограничение в пределах проекта или CWD.
    Защита от path traversal (как в sheets.py v1).
    """
    raw = Path(raw_path)
    project_dir = Path(__file__).resolve().parent
    cwd = Path.cwd().resolve()
    if raw.is_absolute():
        path = raw.resolve()
    else:
        path = (project_dir / raw).resolve()
    if not path.exists():
        logger.warning("[sheets_v2] _resolve_credentials_path_v2: файл не найден: %s", path)
        return None
    try:
        path.resolve().relative_to(project_dir)
        logger.debug("[sheets_v2] _resolve_credentials_path_v2: путь в проекте, ok")
        return path
    except ValueError:
        pass
    try:
        path.resolve().relative_to(cwd)
        logger.debug("[sheets_v2] _resolve_credentials_path_v2: путь в CWD, ok")
        return path
    except ValueError:
        logger.warning("[sheets_v2] google_credentials_path вне каталога проекта/CWD: %s", raw_path)
        return None


def _gc_v2() -> Any:
    """Подключение gspread для V2 (service account)."""
    try:
        import gspread
        settings = get_settings_v2()
        path = _resolve_credentials_path_v2(settings.google_credentials_path)
        if not path:
            logger.warning("[sheets_v2] _gc_v2: путь к credentials не найден или не прошёл проверку")
            return None
        return gspread.service_account(filename=str(path))
    except Exception as e:
        logger.warning("[sheets_v2] _gc_v2: %s", e)
        return None


def get_mapping_from_sheet() -> dict[str, str] | None:
    """
    Читает лист «Маппинг»: колонки «Категория» (или «slug»/«категория») и «Канал» (travel/drinks/lifhaki).
    Возвращает словарь: ключ — подстрока категории/slug, значение — channel key.
    Если таблица недоступна — None (используется default в wordpress_v2).
    """
    gc = _gc_v2()
    if not gc:
        return None
    settings = get_settings_v2()
    sheet_id = (settings.google_sheet_id or "").strip()
    if not sheet_id:
        return None
    try:
        sh = gc.open_by_key(sheet_id)
        ws = sh.worksheet("Маппинг")
    except Exception as e:
        logger.warning("[sheets_v2] get_mapping_from_sheet: лист Маппинг недоступен — %s", e)
        return None
    try:
        rows = ws.get_all_records()
        mapping: dict[str, str] = {}
        for r in rows:
            cat = (r.get("Категория") or r.get("категория") or r.get("slug") or "").strip()
            ch = (r.get("Канал") or r.get("канал") or "").strip().lower()
            if not cat:
                continue
            channel_key = SHEET_CHANNEL_TO_KEY.get(ch) or (ch if ch in (CHANNEL_TRAVEL, CHANNEL_LIFHAKI, CHANNEL_DRINKS) else None)
            if channel_key:
                mapping[cat.lower()] = channel_key
        logger.info("[sheets_v2] get_mapping_from_sheet: загружено правил %s", len(mapping))
        return mapping if mapping else None
    except Exception as e:
        logger.warning("[sheets_v2] get_mapping_from_sheet: %s", e)
        return None


def append_history_row(url: str, platform: str, channel: str, text_preview: str) -> bool:
    """Добавляет строку в лист «История» (лог публикаций V2)."""
    gc = _gc_v2()
    if not gc:
        return False
    settings = get_settings_v2()
    if not (settings.google_sheet_id or "").strip():
        return False
    try:
        sh = gc.open_by_key(settings.google_sheet_id)
        ws = sh.worksheet("История")
        row = [url[:200], platform, channel, text_preview[:500] if text_preview else ""]
        ws.append_row(row, value_input_option="RAW")
        return True
    except Exception as e:
        logger.warning("[sheets_v2] append_history_row: %s", e)
        return False
