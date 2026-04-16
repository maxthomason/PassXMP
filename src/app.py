"""Main application class — lifecycle, tray icon, window management."""

import logging
import os
import threading

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer

from .config.config_manager import ConfigManager
from .config.path_detector import detect_paths
from .gui.setup_window import SetupWindow
from .gui.main_window import MainWindow
from .gui.settings_window import SettingsWindow
from .gui.tray_icon import TrayIcon
from .watcher.folder_watcher import FolderWatcher
from .watcher.mirror import initial_sync
from .utils.logger import setup_logging

logger = logging.getLogger("passxmp.app")


class PassXMPApp(QObject):
    """Top-level application controller."""

    # Thread-safe signal for activity updates from watcher thread
    _activity_signal = pyqtSignal(str, str)

    def __init__(self, config_path: str | None = None):
        super().__init__()
        self.config = ConfigManager(config_path)
        self._watcher: FolderWatcher | None = None
        self._setup_window: SetupWindow | None = None
        self._main_window: MainWindow | None = None
        self._settings_window: SettingsWindow | None = None
        self._tray: TrayIcon | None = None
        self._is_paused = False

    def start(self) -> None:
        """Launch the application — show setup or main window."""
        setup_logging()
        logger.info("PassXMP starting")

        if self.config.is_first_run or not self.config.lightroom_path:
            self._show_setup()
        else:
            self._show_main()
            self._start_watcher()

    def _show_setup(self) -> None:
        detected = detect_paths()
        self._setup_window = SetupWindow(
            detected_lr=detected.get("lightroom", ""),
            detected_dv=detected.get("davinci", ""),
        )
        self._setup_window.setup_complete.connect(self._on_setup_complete)
        self._setup_window.show()

    @pyqtSlot(str, str, int)
    def _on_setup_complete(self, lr_path: str, dv_path: str, lut_size: int) -> None:
        self.config.lightroom_path = lr_path
        self.config.davinci_path = dv_path
        self.config.lut_size = lut_size
        self.config.is_first_run = False
        self.config.save()

        if self._setup_window:
            self._setup_window.close()
            self._setup_window = None

        self._show_main()
        self._run_initial_sync()
        self._start_watcher()

    def _show_main(self) -> None:
        self._main_window = MainWindow()
        self._activity_signal.connect(self._main_window.add_activity)
        self._main_window.sync_all_requested.connect(self._on_sync_all)
        self._main_window.settings_requested.connect(self._show_settings)
        self._main_window.show()

        # System tray
        self._tray = TrayIcon()
        self._tray.show_requested.connect(self._on_show_main)
        self._tray.sync_requested.connect(self._on_sync_all)
        self._tray.pause_requested.connect(self._on_toggle_pause)
        self._tray.quit_requested.connect(self._on_quit)
        self._tray.show()

    def _show_settings(self) -> None:
        self._settings_window = SettingsWindow(
            self.config.lightroom_path,
            self.config.davinci_path,
            self.config.lut_size,
            self.config.auto_start,
        )
        self._settings_window.settings_saved.connect(self._on_settings_saved)
        self._settings_window.show()

    @pyqtSlot(str, str, int, bool)
    def _on_settings_saved(self, lr: str, dv: str, size: int, auto_start: bool) -> None:
        paths_changed = (lr != self.config.lightroom_path or
                         dv != self.config.davinci_path or
                         size != self.config.lut_size)

        self.config.lightroom_path = lr
        self.config.davinci_path = dv
        self.config.lut_size = size
        self.config.auto_start = auto_start
        self.config.save()

        if paths_changed:
            self._stop_watcher()
            self._start_watcher()
            self._run_initial_sync()

    def _start_watcher(self) -> None:
        lr = self.config.lightroom_path
        dv = self.config.davinci_path
        if not lr or not dv:
            return

        self._watcher = FolderWatcher(
            lr, dv, self.config.lut_size,
            on_sync=self._on_file_synced,
        )
        self._watcher.start()
        self._is_paused = False

        if self._main_window:
            self._main_window.set_status(True)
        if self._tray:
            self._tray.set_syncing(True)

    def _stop_watcher(self) -> None:
        if self._watcher:
            self._watcher.stop()
            self._watcher = None

    def _on_file_synced(self, xmp_rel: str, cube_rel: str) -> None:
        """Called from watcher thread — emit signal for thread-safe GUI update."""
        self._activity_signal.emit(xmp_rel, cube_rel)

    def _run_initial_sync(self) -> None:
        """Run initial sync in a background thread."""
        lr = self.config.lightroom_path
        dv = self.config.davinci_path
        size = self.config.lut_size

        def _sync():
            converted, total = initial_sync(lr, dv, size)
            logger.info("Initial sync: %d converted out of %d total", converted, total)
            if self._main_window:
                self._main_window.set_synced_count(total)

        thread = threading.Thread(target=_sync, daemon=True)
        thread.start()

    @pyqtSlot()
    def _on_sync_all(self) -> None:
        self._run_initial_sync()
        if self._tray:
            self._tray.show_message("PassXMP", "Full sync started...")

    @pyqtSlot()
    def _on_toggle_pause(self) -> None:
        if self._is_paused:
            self._start_watcher()
        else:
            self._stop_watcher()
            self._is_paused = True
            if self._main_window:
                self._main_window.set_status(False)
            if self._tray:
                self._tray.set_syncing(False)

    @pyqtSlot()
    def _on_show_main(self) -> None:
        if self._main_window:
            self._main_window.show()
            self._main_window.raise_()
            self._main_window.activateWindow()

    @pyqtSlot()
    def _on_quit(self) -> None:
        self._stop_watcher()
        QApplication.quit()
