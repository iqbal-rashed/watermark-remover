"""Centralised logging configuration for all entry points.

Call setup_logging() once at startup (desktop.py / cli.py).
All other modules just do `from loguru import logger` and log normally.
"""
import sys
from pathlib import Path

from loguru import logger

APP_DATA = Path.home() / ".watermark-remover"
LOGS_DIR = APP_DATA / "logs"

_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{name}:{function}:{line} - {message}"
)
_CONSOLE_FORMAT = "<level>{level: <8}</level> | <cyan>{name}</cyan>:{line} - {message}"


def setup_logging(
    mode: str = "app",
    level: str = "INFO",
    console_level: str = "WARNING",
    console: bool = False,
) -> Path:
    """Configure loguru to write logs to ~/.watermark-remover/logs/<mode>.log.

    Args:
        mode:          Log filename prefix: "desktop", "cli", or "server".
        level:         Minimum log level written to the file.
        console_level: Minimum level printed to stderr (only when console=True).
        console:       If True, attach a stderr sink (useful for CLI mode).

    Returns:
        Path to the active log file.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"{mode}.log"

    logger.remove()  # clear default sink

    # ── File sink ─────────────────────────────────────────────────────────────
    logger.add(
        log_file,
        format=_FILE_FORMAT,
        level=level,
        rotation="10 MB",
        retention=5,
        compression="zip",
        encoding="utf-8",
        enqueue=True,   # thread-safe writes from multiple threads
        backtrace=True,
        diagnose=True,
    )

    # ── Optional stderr sink (CLI) ─────────────────────────────────────────────
    if console:
        logger.add(
            sys.stderr,
            format=_CONSOLE_FORMAT,
            level=console_level,
            colorize=True,
            enqueue=False,
        )

    logger.info(f"Logging started [mode={mode}, level={level}, file={log_file}]")
    return log_file


def get_log_dir() -> Path:
    """Return the logs directory path (creates it if needed)."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR


def get_log_file(mode: str = "app") -> Path:
    """Return the path for a given mode's log file."""
    return LOGS_DIR / f"{mode}.log"
