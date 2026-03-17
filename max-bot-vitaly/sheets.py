"""Google Таблица: маппинг категорий, лог публикаций."""
import logging
from pathlib import Path
from typing import Any

from config import CHANNEL_DRINKS, CHANNEL_LIFHAKI, CHANNEL_TRAVEL, get_settings

logger = logging.getLogger(__name__)

SHEET_CHANNEL_TO_KEY = {
    "travel": CHANNEL_TRAVEL, "путешествия": CHANNEL_TRAVEL,
    "drinks": CHANNEL_DRINKS, "напитки": CHANNEL_DRINKS,
    "lifhaki": CHANNEL_LIFHAKI, "лайфхаки": CHANNEL_LIFHAKI,
}


def _resolve_credentials_path(raw_path: str | Path) -> Path | None:
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
        return path
    except ValueError:
        pass
    try:
        path.resolve().relative_to(cwd)
        return path
    except ValueError:
        logger.warning("[sheets] google_credentials_path вне каталога проекта/CWD: %s", raw_path)
        return None


def _gc() -> Any:
    try:
        import gspread
        settings = get_settings()
        path = _resolve_credentials_path(settings.google_credentials_path)
        if not path:
            logger.warning("[sheets] _gc: путь к credentials не найден")
            return None
        return gspread.service_account(filename=str(path))
    except Exception as e:
        logger.warning("[sheets] _gc: %s", e)
        return None


def get_mapping_from_sheet() -> dict[str, str] | None:
    gc = _gc()
    if not gc:
        return None
    settings = get_settings()
    sheet_id = (settings.google_sheet_id or "").strip()
    if not sheet_id:
        return None
    try:
        sh = gc.open_by_key(sheet_id)
        ws = sh.worksheet("Маппинг")
    except Exception as e:
        logger.warning("[sheets] get_mapping_from_sheet: лист Маппинг недоступен — %s", e)
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
        logger.info("[sheets] get_mapping_from_sheet: загружено правил %s", len(mapping))
        return mapping if mapping else None
    except Exception as e:
        logger.warning("[sheets] get_mapping_from_sheet: %s", e)
        return None


def append_history_row(url: str, platform: str, channel: str, text_preview: str) -> bool:
    gc = _gc()
    if not gc:
        return False
    settings = get_settings()
    if not (settings.google_sheet_id or "").strip():
        return False
    try:
        sh = gc.open_by_key(settings.google_sheet_id)
        ws = sh.worksheet("История")
        row = [url[:200], platform, channel, text_preview[:500] if text_preview else ""]
        ws.append_row(row, value_input_option="RAW")
        return True
    except Exception as e:
        logger.warning("[sheets] append_history_row: %s", e)
        return False
