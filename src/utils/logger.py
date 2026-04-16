"""Logging setup for PassXMP.

Configures file + console logging. The GUI activity feed reads from
a custom handler that emits log records to a callback.
"""

import logging
import os
import platform
from logging.handlers import RotatingFileHandler


def _log_dir() -> str:
    system = platform.system()
    if system == "Darwin":
        return os.path.expanduser("~/Library/Logs/PassXMP")
    elif system == "Windows":
        appdata = os.environ.get("LOCALAPPDATA",
                                 os.environ.get("APPDATA", os.path.expanduser("~")))
        return os.path.join(appdata, "PassXMP", "logs")
    else:
        return os.path.expanduser("~/.local/share/passxmp/logs")


class CallbackHandler(logging.Handler):
    """Logging handler that forwards records to a callback function.

    Used by the GUI to display log messages in the activity feed.
    """

    def __init__(self, callback: callable):
        super().__init__()
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.callback(msg)
        except Exception:
            self.handleError(record)


def setup_logging(
    level: int = logging.INFO,
    gui_callback: callable = None,
) -> logging.Logger:
    """Configure the passxmp logger.

    Args:
        level: Logging level.
        gui_callback: Optional callback for GUI activity feed.

    Returns:
        The configured root passxmp logger.
    """
    logger = logging.getLogger("passxmp")
    logger.setLevel(level)

    # Avoid duplicate handlers on re-init
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler
    try:
        log_dir = _log_dir()
        os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "passxmp.log"),
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        logger.warning("Could not create log file, file logging disabled")

    # GUI callback handler
    if gui_callback:
        cb_handler = CallbackHandler(gui_callback)
        cb_handler.setLevel(logging.INFO)
        cb_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(cb_handler)

    return logger
