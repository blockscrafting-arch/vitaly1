"""Выбор следующего материала для канала: по кругу / вразнобой с учётом антидублей."""
import logging
import random
import time

from config_v2 import get_settings_v2
from db_v2 import get_catalog_for_channel, get_rotation_state, set_rotation_state

logger = logging.getLogger(__name__)


async def get_next_item_for_channel(
    channel: str,
    mode: str = "round",  # "round" | "random" | "hybrid" (hybrid = 50% round, 50% random)
    subcategory_gap: bool = True,
) -> tuple[int, str, str, str, str] | None:
    """
    Возвращает следующий материал для канала: (id, url, title, excerpt, subcategory).
    Учитывает repeat_interval_days и опционально subcategory_gap.
    """
    settings = get_settings_v2()
    cutoff_ts = int(time.time()) - settings.repeat_interval_days * 86400
    rows = await get_catalog_for_channel(
        channel,
        exclude_urls_seen_after_ts=cutoff_ts,
        limit=2000,
    )
    if not rows:
        logger.warning("[router_v2] get_next_item_for_channel: пустой пул для канала %s", channel)
        return None

    # Исключить подкатегорию последнего поста (subcategory_gap)
    if subcategory_gap:
        last_sub = await get_rotation_state(f"last_subcategory_{channel}")
        if last_sub:
            rows = [r for r in rows if (r[4] or "") != last_sub]
        if not rows:
            rows = await get_catalog_for_channel(channel, exclude_urls_seen_after_ts=cutoff_ts, limit=2000)

    if not rows:
        return None

    # Режим: round — по кругу, random — случайно, hybrid — 50/50
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
    # Обновить pointer для round в следующий раз (текущая позиция в списке)
    try:
        idx = next(i for i, r in enumerate(rows) if r[0] == chosen[0])
        await set_rotation_state(f"pointer_{channel}", value_int=(idx + 1) % len(rows))
    except StopIteration:
        pass
    await set_rotation_state(f"last_subcategory_{channel}", value_text=(chosen[4] or ""))
    return chosen
