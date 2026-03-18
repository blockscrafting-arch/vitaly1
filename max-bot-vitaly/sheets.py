"""Google Таблица: маппинг категорий, лог публикаций, расписание, промпты, настройки."""
import logging
import time
from pathlib import Path
from typing import Any

from config import CHANNEL_DRINKS, CHANNEL_LIFHAKI, CHANNEL_TRAVEL, get_settings

logger = logging.getLogger(__name__)
CACHE_TTL_SEC = 600  # 10 минут
_schedule_cache: list[dict[str, Any]] | None = None
_schedule_cache_ts: float = 0
_prompts_cache: dict[str, str] | None = None
_prompts_cache_ts: float = 0
_settings_cache: dict[str, str] | None = None
_settings_cache_ts: float = 0

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
        row = [url[:200], platform, channel, (text_preview[:2000] if text_preview else "").strip()]
        ws.append_row(row, value_input_option="RAW")
        return True
    except Exception as e:
        logger.warning("[sheets] append_history_row: %s", e)
        return False


def _get_sheet_worksheet(name: str) -> Any:
    gc = _gc()
    if not gc:
        return None
    settings = get_settings()
    sheet_id = (settings.google_sheet_id or "").strip()
    if not sheet_id:
        return None
    try:
        return gc.open_by_key(sheet_id).worksheet(name)
    except Exception as e:
        logger.debug("[sheets] лист %s недоступен: %s", name, e)
        return None


def get_schedule_from_sheet() -> list[dict[str, Any]] | None:
    """Читает лист «Расписание». Колонки: Канал, Тип, День, Время. Кэш 10 мин."""
    global _schedule_cache, _schedule_cache_ts
    if _schedule_cache is not None and (time.time() - _schedule_cache_ts) < CACHE_TTL_SEC:
        return _schedule_cache
    ws = _get_sheet_worksheet("Расписание")
    if not ws:
        return None
    try:
        rows = ws.get_all_records()
        result: list[dict[str, Any]] = []
        for r in rows:
            ch = (r.get("Канал") or r.get("канал") or "").strip().lower()
            slot_type = (r.get("Тип") or r.get("тип") or "main").strip().lower()
            day = (r.get("День") or r.get("день") or "*").strip().lower()
            t = (r.get("Время") or r.get("время") or "").strip()
            if ch and t:
                channel_key = SHEET_CHANNEL_TO_KEY.get(ch) or (ch if ch in (CHANNEL_TRAVEL, CHANNEL_LIFHAKI, CHANNEL_DRINKS) else ch)
                result.append({"channel": channel_key, "slot_type": slot_type, "day": day, "time": t})
        _schedule_cache = result if result else []
        _schedule_cache_ts = time.time()
        logger.info("[sheets] get_schedule_from_sheet: загружено слотов %s", len(_schedule_cache))
        return _schedule_cache
    except Exception as e:
        logger.warning("[sheets] get_schedule_from_sheet: %s", e)
        return None


def get_prompts_from_sheet() -> dict[str, str] | None:
    """Читает лист «Промпты». Колонки: Ключ (или Тип/Канал), Текст. Кэш 10 мин."""
    global _prompts_cache, _prompts_cache_ts
    if _prompts_cache is not None and (time.time() - _prompts_cache_ts) < CACHE_TTL_SEC:
        return _prompts_cache
    ws = _get_sheet_worksheet("Промпты")
    if not ws:
        return None
    try:
        rows = ws.get_all_records()
        result: dict[str, str] = {}
        for r in rows:
            key = (r.get("Ключ") or r.get("ключ") or r.get("Тип") or r.get("тип") or "").strip().lower()
            text = (r.get("Текст") or r.get("текст") or "").strip()
            if key and text:
                result[key] = text
        _prompts_cache = result if result else {}
        _prompts_cache_ts = time.time()
        logger.info("[sheets] get_prompts_from_sheet: загружено промптов %s", len(_prompts_cache))
        return _prompts_cache
    except Exception as e:
        logger.warning("[sheets] get_prompts_from_sheet: %s", e)
        return None


def get_settings_from_sheet() -> dict[str, str] | None:
    """Читает лист «Настройки». Колонки: Ключ, Значение. Кэш 10 мин."""
    global _settings_cache, _settings_cache_ts
    if _settings_cache is not None and (time.time() - _settings_cache_ts) < CACHE_TTL_SEC:
        return _settings_cache
    ws = _get_sheet_worksheet("Настройки")
    if not ws:
        return None
    try:
        rows = ws.get_all_records()
        result: dict[str, str] = {}
        for r in rows:
            k = (r.get("Ключ") or r.get("ключ") or "").strip()
            v = (r.get("Значение") or r.get("значение") or "").strip()
            if k:
                result[k] = v
        _settings_cache = result if result else {}
        _settings_cache_ts = time.time()
        logger.info("[sheets] get_settings_from_sheet: загружено настроек %s", len(_settings_cache))
        return _settings_cache
    except Exception as e:
        logger.warning("[sheets] get_settings_from_sheet: %s", e)
        return None


def invalidate_sheets_cache() -> None:
    """Сбрасывает кэш листов (после изменения расписания/промптов/настроек)."""
    global _schedule_cache, _schedule_cache_ts, _prompts_cache, _prompts_cache_ts, _settings_cache, _settings_cache_ts
    _schedule_cache = None
    _schedule_cache_ts = 0
    _prompts_cache = None
    _prompts_cache_ts = 0
    _settings_cache = None
    _settings_cache_ts = 0
