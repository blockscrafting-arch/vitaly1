"""Выбор следующего материала для канала: по кругу / вразнобой с учётом антидублей."""
import logging
import random
import time

from config import get_settings
from db import get_catalog_for_channel, get_rotation_state, set_rotation_state

logger = logging.getLogger(__name__)


def _get_repeat_interval_days() -> int:
    """Sheet > config > default."""
    from sheets import get_setting_value
    v = get_setting_value("repeat_interval_days", "")
    if v:
        try:
            return int(v)
        except ValueError:
            pass
    return get_settings().repeat_interval_days


async def get_next_item_for_channel(
    channel: str,
    mode: str = "round",
    subcategory_gap: bool = True,
) -> tuple[int, str, str, str, str] | None:
    from sheets import get_setting_value
    sheet_mode = get_setting_value("selection_mode", "").lower()
    if sheet_mode in ("round", "random", "hybrid"):
        mode = sheet_mode
    sheet_sub = get_setting_value("subcategory_gap", "").lower()
    if sheet_sub in ("false", "0", "no"):
        subcategory_gap = False
    elif sheet_sub in ("true", "1", "yes"):
        subcategory_gap = True
    repeat_days = _get_repeat_interval_days()
    cutoff_ts = int(time.time()) - repeat_days * 86400
    rows = await get_catalog_for_channel(channel, exclude_urls_seen_after_ts=cutoff_ts, limit=2000)
    if not rows:
        logger.warning("[router] get_next_item_for_channel: пустой пул для канала %s", channel)
        return None
    if subcategory_gap:
        last_sub = await get_rotation_state(f"last_subcategory_{channel}")
        if last_sub:
            rows = [r for r in rows if (r[4] or "") != last_sub]
        if not rows:
            rows = await get_catalog_for_channel(channel, exclude_urls_seen_after_ts=cutoff_ts, limit=2000)
    if not rows:
        return None
    use_round = True
    if mode == "random":
        use_round = False
    elif mode == "hybrid":
        use_round = random.random() < 0.5
    if use_round:
        pointer = await get_rotation_state(f"pointer_{channel}")
        idx = int(pointer) if pointer is not None else 0
        idx = idx % len(rows) if rows else 0
        chosen = rows[idx]
        await set_rotation_state(f"pointer_{channel}", value_int=(idx + 1) % len(rows))
        await set_rotation_state(f"last_subcategory_{channel}", value_text=(chosen[4] or ""))
        return chosen
    chosen = random.choice(rows)
    try:
        idx = next(i for i, r in enumerate(rows) if r[0] == chosen[0])
        await set_rotation_state(f"pointer_{channel}", value_int=(idx + 1) % len(rows))
    except StopIteration:
        pass
    await set_rotation_state(f"last_subcategory_{channel}", value_text=(chosen[4] or ""))
    return chosen
