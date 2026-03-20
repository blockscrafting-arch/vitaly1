"""Единая настройка логов с временем Europe/Moscow (независимо от TZ сервера)."""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

MSK = ZoneInfo("Europe/Moscow")
_DEFAULT_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


class MoscowFormatter(logging.Formatter):
    """%(asctime)s в московском времени."""

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        *,
        tz: ZoneInfo = MSK,
    ) -> None:
        super().__init__(fmt or _DEFAULT_FMT, datefmt or _DEFAULT_DATEFMT)
        self._tz = tz

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """Как в стандартном Formatter: дата/время + миллисекунды через запятую."""
        dt = datetime.fromtimestamp(record.created, tz=self._tz)
        fmt = datefmt or self.datefmt
        time_str = dt.strftime(fmt) if fmt else dt.strftime(_DEFAULT_DATEFMT)
        ms = int(record.msecs)
        return f"{time_str},{ms:03d}"


def configure_root_logging(level: int = logging.INFO) -> None:
    """Настраивает root-логгер: stdout + время МСК (APScheduler и все модули)."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(MoscowFormatter(_DEFAULT_FMT, _DEFAULT_DATEFMT))
    root.addHandler(h)
