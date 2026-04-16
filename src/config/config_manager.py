"""User configuration management (JSON-based)."""

import json
import logging
import os
import platform

logger = logging.getLogger("passxmp.config")

DEFAULT_CONFIG = {
    "lightroom_presets_path": "",
    "davinci_lut_path": "",
    "lut_size": 33,
    "auto_start": False,
    "first_run": True,
    "selected_relative_paths": [],
}


def _config_dir() -> str:
    """Get the platform-appropriate config directory."""
    system = platform.system()
    if system == "Darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif system == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return os.path.join(base, "PassXMP")


class ConfigManager:
    """Read/write user configuration as JSON."""

    def __init__(self, config_path: str | None = None):
        if config_path:
            self._path = config_path
        else:
            self._path = os.path.join(_config_dir(), "config.json")
        self._data: dict = {}
        self.load()

    def load(self) -> None:
        """Load config from disk, using defaults for missing keys."""
        self._data = dict(DEFAULT_CONFIG)
        if os.path.exists(self._path):
            try:
                with open(self._path, "r") as f:
                    stored = json.load(f)
                self._data.update(stored)
            except (json.JSONDecodeError, OSError):
                logger.warning("Failed to load config, using defaults")

    def save(self) -> None:
        """Persist config to disk atomically.

        Writing to a temp file first and renaming over the real config
        prevents a crash or power loss mid-write from producing an
        unparseable JSON document — which would silently reset every
        user setting the next time the app loads.
        """
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        tmp_path = self._path + ".tmp"
        try:
            with open(tmp_path, "w") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp_path, self._path)
        except BaseException:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise
        logger.debug("Config saved to %s", self._path)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value

    @property
    def lightroom_path(self) -> str:
        return self._data.get("lightroom_presets_path", "")

    @lightroom_path.setter
    def lightroom_path(self, value: str) -> None:
        self._data["lightroom_presets_path"] = value

    @property
    def davinci_path(self) -> str:
        return self._data.get("davinci_lut_path", "")

    @davinci_path.setter
    def davinci_path(self, value: str) -> None:
        self._data["davinci_lut_path"] = value

    @property
    def lut_size(self) -> int:
        return self._data.get("lut_size", 33)

    @lut_size.setter
    def lut_size(self, value: int) -> None:
        self._data["lut_size"] = value

    @property
    def is_first_run(self) -> bool:
        return self._data.get("first_run", True)

    @is_first_run.setter
    def is_first_run(self, value: bool) -> None:
        self._data["first_run"] = value

    @property
    def auto_start(self) -> bool:
        return self._data.get("auto_start", False)

    @auto_start.setter
    def auto_start(self, value: bool) -> None:
        self._data["auto_start"] = value

    @property
    def selected_relative_paths(self) -> list[str]:
        value = self._data.get("selected_relative_paths")
        return list(value) if isinstance(value, list) else []

    @selected_relative_paths.setter
    def selected_relative_paths(self, value: list[str]) -> None:
        self._data["selected_relative_paths"] = list(value)
