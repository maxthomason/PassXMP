"""File-only logging setup for PassXMP."""

import logging
import os
import platform
from logging.handlers import RotatingFileHandler

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
_BACKUP_COUNT = 3             # keep passxmp.log + 3 rotated siblings


def _log_dir() -> str:
    system = platform.system()
    if system == "Darwin":
        base = os.path.expanduser("~/Library/Logs/PassXMP")
    elif system == "Windows":
        base = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                            "PassXMP", "Logs")
    else:
        base = os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
        base = os.path.join(base, "PassXMP")
    os.makedirs(base, exist_ok=True)
    return base


def setup_logging() -> None:
    """Configure root logger to write to the platform log directory only.

    The GUI no longer mirrors log records — logs are file-only.
    """
    root = logging.getLogger("passxmp")
    if root.handlers:
        return
    root.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        os.path.join(_log_dir(), "passxmp.log"),
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    root.addHandler(handler)
