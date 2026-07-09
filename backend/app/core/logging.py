"""
NutriBudget AI - Centralized Logging Configuration

Usage in any module:
    from app.core.logging import get_logger
    logger = get_logger(__name__)

    logger.debug("Detailed step")
    logger.info("Success")
    logger.warning("Degraded mode, using fallback")
    logger.error("Operation failed", exc_info=True)
    logger.critical("Fatal - application cannot continue")

Visual Format (console):
    20:36:01.234  DEBUG    ai.qwen3_client        | HF/featherless-ai: POST > https://router.huggingface.co/...
    20:36:02.105  INFO     services.ai.orchestr.  | OK Provider 'Qwen3' succeeded in 1842.3ms for '2 rotis'
    20:36:03.001  WARNING  services.ai.orchestr.  | Provider 'Qwen3' failed after 15001.0ms: HTTP 503
    20:36:04.880  ERROR    services.ai.qwen_vl    | HF/novita: request failed - ConnectionError
"""

import logging
import sys
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# ANSI Colour Codes
# ─────────────────────────────────────────────────────────────────────────────

_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"

# Text colours
_WHITE    = "\033[97m"
_CYAN     = "\033[36m"
_GREEN    = "\033[32m"
_YELLOW   = "\033[33m"
_RED      = "\033[31m"
_MAGENTA  = "\033[35m"
_BLUE     = "\033[34m"

# Level → colour + symbol prefix mapping (ASCII-safe for Windows cp1252 terminals)
_LEVEL_STYLES: dict[int, tuple[str, str]] = {
    logging.DEBUG:    (_DIM + _WHITE,    "·"),
    logging.INFO:     (_CYAN,            ">"),
    logging.WARNING:  (_YELLOW,          "!"),
    logging.ERROR:    (_RED,             "X"),
    logging.CRITICAL: (_BOLD + _MAGENTA, "!!"),
}

# Module-name colour (dim blue to visually separate from message)
_NAME_COLOUR = _DIM + _BLUE


# ─────────────────────────────────────────────────────────────────────────────
# Custom Formatter
# ─────────────────────────────────────────────────────────────────────────────

class _ColourFormatter(logging.Formatter):
    """
    Coloured single-line log formatter.

    Output:
        HH:MM:SS.mmm  LEVEL    module.submodule     | message
    """

    def format(self, record: logging.LogRecord) -> str:
        level_colour, emoji = _LEVEL_STYLES.get(record.levelno, (_WHITE, "?"))

        # Shorten logger name: strip "app." prefix and limit width
        name = record.name
        if name.startswith("app."):
            name = name[4:]
        name_str = f"{_NAME_COLOUR}{name:<26}{_RESET}"

        # Timestamp: HH:MM:SS.mmm
        ts = self.formatTime(record, "%H:%M:%S")
        ms = int(record.msecs)
        timestamp = f"{_DIM}{ts}.{ms:03d}{_RESET}"

        # Level label (padded to 8 chars)
        level_label = f"{level_colour}{record.levelname:<8}{_RESET}"

        # Message (with exception if present)
        msg = record.getMessage()
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)

        return f"{timestamp}  {level_label}  {name_str}  {emoji} {msg}"


class _PlainFormatter(logging.Formatter):
    """
    Plain formatter for file output (no ANSI codes).
    """

    def format(self, record: logging.LogRecord) -> str:
        name = record.name
        if name.startswith("app."):
            name = name[4:]

        ts = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        ms = int(record.msecs)

        msg = record.getMessage()
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)

        return f"{ts}.{ms:03d}  {record.levelname:<8}  {name:<26}  {msg}"


# ─────────────────────────────────────────────────────────────────────────────
# Setup — called ONCE from main.py
# ─────────────────────────────────────────────────────────────────────────────

def setup_logging(
    level: int = logging.DEBUG,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure the root logger for the entire application.

    Works alongside uvicorn's logging - does NOT wipe uvicorn's handlers.
    Instead it installs our ColourFormatter handler once (idempotent) and
    then ensures all app.* loggers propagate up to root.

    Args:
        level:    Minimum log level (default DEBUG in dev, INFO in prod).
        log_file: Optional path to write plain-text logs alongside console.
    """
    root = logging.getLogger()
    root.setLevel(level)

    # ── Console handler ────────────────────────────────────────────────────
    # Only add if we haven't already (idempotent — safe across --reload cycles)
    already_installed = any(
        isinstance(h, logging.StreamHandler)
        and isinstance(h.formatter, _ColourFormatter)
        for h in root.handlers
    )
    if not already_installed:
        # On Windows the terminal may use cp1252 — try to switch stderr to UTF-8,
        # fall back to errors='replace' so Unicode never silently kills a log line.
        stream = sys.stderr
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        console = logging.StreamHandler(stream)
        console.setLevel(level)
        console.setFormatter(_ColourFormatter())
        root.addHandler(console)

    # ── File handler (plain, optional) ────────────────────────────────────
    file_already = any(isinstance(h, logging.FileHandler) for h in root.handlers)
    if log_file and not file_already:
        import os
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(_PlainFormatter())
        root.addHandler(fh)

    # ── Ensure all app.* loggers propagate to root ────────────────────────
    # (they should by default, but explicit is safer)
    logging.getLogger("app").setLevel(level)
    logging.getLogger("app").propagate = True

    # ── Silence noisy third-party loggers ────────────────────────────────
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    # Keep uvicorn.access quiet (it has its own formatted output)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    # But let uvicorn.error through so startup/shutdown messages still appear
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


# ─────────────────────────────────────────────────────────────────────────────
# Factory — use this in every module
# ─────────────────────────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.

    Call at module level:
        logger = get_logger(__name__)
    """
    return logging.getLogger(name)