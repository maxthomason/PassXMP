"""File-only logging setup for PassXMP."""

import logging
import os
import platform


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
    handler = logging.FileHandler(os.path.join(_log_dir(), "passxmp.log"))
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    root.addHandler(handler)
