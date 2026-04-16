"""Main application class — lifecycle, tray icon, registry-driven sync."""

import logging
import os
import shutil
import threading
import time

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from .config.config_manager import ConfigManager
from .config.path_detector import detect_paths
from .core.file_registry import FileRegistry, FileState
from .core.sync_engine import process_xmp_file
from .gui.main_window import MainWindow
from .gui.tray_icon import TrayIcon
from .watcher.folder_watcher import FolderWatcher
from .watcher.mirror import get_mirror_path
from .utils.logger import setup_logging

logger = logging.getLogger("passxmp.app")


class PassXMPApp(QObject):
    """Top-level application controller."""

    _row_syncing = pyqtSignal(str)                       # xmp_path
    _row_done = pyqtSignal(str, bool, str)               # xmp_path, ok, err
    _progress = pyqtSignal(str, str, int, int, int)      # name, folder, cur, total, bytes
    _idle = pyqtSignal()
    _watcher_created = pyqtSignal(str)
    _watcher_modified = pyqtSignal(str)
    _watcher_deleted = pyqtSignal(str)

    def __init__(self, config_path: str | None = None):
        super().__init__()
        self.config = ConfigManager(config_path)
        self._registry = FileRegistry()
        self._watcher: FolderWatcher | None = None
        self._main_window: MainWindow | None = None
        self._tray: TrayIcon | None = None
        self._is_paused = False
        self._detected: dict[str, str] = {}

        self._sync_thread: threading.Thread | None = None
        self._sync_cancel = threading.Event()
        self._last_sync_ts: float | None = None

    def start(self) -> None:
        setup_logging()
        logger.info("PassXMP starting")

        self._detected = detect_paths()
        self._show_main()

        lr = self.config.lightroom_path
        dv = self.config.davinci_path
        if lr and dv:
            self._registry.rescan(lr, dv)
            self._restore_selection()
            if self.config.auto_start or not self.config.is_first_run:
                self._start_watcher()

    # ----- window wiring -----

    def _show_main(self) -> None:
        lr = self.config.lightroom_path or self._detected.get("lightroom", "")
        dv = self.config.davinci_path or self._detected.get("davinci", "")

        self._main_window = MainWindow(
            registry=self._registry,
            lr_path=lr, dv_path=dv,
            lut_size=self.config.lut_size,
            auto_start=self.config.auto_start,
            default_lr=self._detected.get("lightroom", ""),
            default_dv=self._detected.get("davinci", ""),
        )

        if not self.config.lightroom_path and lr:
            self.config.lightroom_path = lr
        if not self.config.davinci_path and dv:
            self.config.davinci_path = dv
        if self.config.is_first_run:
            self.config.is_first_run = False
            self.config.save()

        self._main_window.config_changed.connect(self._on_config_changed)
        self._main_window.sync_requested.connect(self._on_sync_requested)
        self._main_window.stop_requested.connect(self._on_stop_requested)
        self._main_window.pause_toggled.connect(self._on_pause_toggled)

        self._row_syncing.connect(self._registry.mark_syncing)
        self._row_done.connect(
            lambda p, ok, err: self._registry.mark_done(p, ok, err or None)
        )
        self._progress.connect(self._on_progress_ui)
        self._idle.connect(self._on_idle_ui)
        self._watcher_created.connect(self._registry.on_watcher_created)
        self._watcher_modified.connect(self._registry.on_watcher_modified)
        self._watcher_deleted.connect(self._registry.on_watcher_deleted)

        self._main_window.show()

        configured = bool(self.config.lightroom_path and self.config.davinci_path)
        self._main_window.presets_view().set_folders_configured(configured)

        self._tray = TrayIcon()
        self._tray.show_requested.connect(self._on_show_main)
        self._tray.sync_requested.connect(self._on_tray_sync_all)
        self._tray.pause_requested.connect(self._on_tray_pause)
        self._tray.quit_requested.connect(self._on_quit)
        self._tray.show()

    # ----- config changes -----

    @pyqtSlot(str, str, int, bool)
    def _on_config_changed(self, lr: str, dv: str, size: int, auto_start: bool) -> None:
        paths_changed = (
            lr != self.config.lightroom_path
            or dv != self.config.davinci_path
            or size != self.config.lut_size
        )

        self.config.lightroom_path = lr
        self.config.davinci_path = dv
        self.config.lut_size = size
        self.config.auto_start = auto_start
        self.config.save()

        if self._main_window:
            self._main_window.presets_view().set_folders_configured(bool(lr and dv))

        if paths_changed and lr and dv:
            self._stop_watcher()
            self._cancel_running_sync()
            self._registry.rescan(lr, dv)
            self._restore_selection()
            self._start_watcher()

    def _restore_selection(self) -> None:
        saved = self.config.selected_relative_paths
        if saved:
            self._registry.restore_selection(saved)
        else:
            self._registry.select_defaults()

    # ----- sync requests -----

    @pyqtSlot(list)
    def _on_sync_requested(self, selected_rows: list) -> None:
        if not selected_rows:
            return
        if not self._confirm_sync_size(selected_rows):
            return
        self._cancel_running_sync()

        snapshot: list[FileState] = list(selected_rows)
        size = self.config.lut_size
        cancel = self._sync_cancel

        def _run() -> None:
            bytes_cum = 0
            total = len(snapshot)
            for i, row in enumerate(snapshot, start=1):
                if cancel.is_set():
                    break
                self._row_syncing.emit(row.xmp_path)
                try:
                    ok = process_xmp_file(row.xmp_path, row.cube_path, size)
                    err = None if ok else "Conversion returned false"
                except Exception as exc:
                    ok = False
                    err = str(exc)
                self._row_done.emit(row.xmp_path, ok, err or "")
                if ok:
                    try:
                        bytes_cum += os.path.getsize(row.cube_path)
                    except OSError:
                        pass
                name = os.path.basename(row.xmp_path)
                self._progress.emit(name, row.folder, i, total, bytes_cum)
            self._last_sync_ts = time.time()
            self._idle.emit()

        self._sync_thread = threading.Thread(target=_run, daemon=True)
        self._sync_thread.start()

    @pyqtSlot()
    def _on_stop_requested(self) -> None:
        self._sync_cancel.set()

    @pyqtSlot(str, str, int, int, int)
    def _on_progress_ui(self, name: str, folder: str, cur: int, total: int, bytes_cum: int) -> None:
        if self._main_window is None:
            return
        avg = bytes_cum / cur if cur > 0 else 0
        projected = int(avg * total)
        footer = self._main_window.presets_view().footer()
        footer.set_active(
            current_name=name, folder=folder,
            current_index=cur, total=total,
            bytes_written=bytes_cum, bytes_projected=projected,
        )

    @pyqtSlot()
    def _on_idle_ui(self) -> None:
        if self._main_window is None:
            return
        self.config.selected_relative_paths = self._registry.selected_relative_paths()
        self.config.save()
        selected = len(self._registry.selected_rows())
        last = (time.strftime("%H:%M", time.localtime(self._last_sync_ts))
                if self._last_sync_ts else None)
        self._main_window.presets_view().footer().set_idle(
            last_sync_iso=last, selected_count=selected,
        )

    # ----- watcher -----

    def _start_watcher(self) -> None:
        lr = self.config.lightroom_path
        dv = self.config.davinci_path
        if not lr or not dv:
            return
        self._watcher = FolderWatcher(
            lr, dv, self.config.lut_size,
            on_sync=self._on_watcher_file_synced,
            on_event=self._on_watcher_event,
        )
        self._watcher.start()
        self._is_paused = False
        if self._main_window:
            self._main_window.presets_view().set_watcher_running(True)
            self._main_window.settings_view().set_watcher_running(True)
        if self._tray:
            self._tray.set_syncing(True)

    def _stop_watcher(self) -> None:
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
        self._is_paused = True
        if self._main_window:
            self._main_window.presets_view().set_watcher_running(False)
            self._main_window.settings_view().set_watcher_running(False)
        if self._tray:
            self._tray.set_syncing(False)

    def _on_watcher_file_synced(self, xmp_rel: str, _cube_rel: str) -> None:
        # Use the watcher's frozen lr_root (captured at start()) rather than
        # config.lightroom_path — if the user changed the LR path while the
        # watcher was running, the new config value won't match the absolute
        # path the registry has indexed.
        lr = self._watcher.lr_root if self._watcher else self.config.lightroom_path
        xmp_abs = os.path.join(lr, xmp_rel) if lr else xmp_rel
        self._row_done.emit(xmp_abs, True, "")

    def _on_watcher_event(self, kind: str, xmp_path: str, _new_path: str | None = None) -> None:
        if kind == "created":
            self._watcher_created.emit(xmp_path)
        elif kind == "modified":
            self._watcher_modified.emit(xmp_path)
        elif kind == "deleted":
            self._watcher_deleted.emit(xmp_path)

    # ----- misc -----

    def _cancel_running_sync(self) -> None:
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_cancel.set()
            self._sync_thread.join(timeout=5.0)
        self._sync_cancel = threading.Event()
        self._sync_thread = None

    def _confirm_sync_size(self, rows: list) -> bool:
        size = self.config.lut_size
        # Measured: ~1.2 MB per 33³ cube (35,937 lines × ~26 bytes),
        # ~10.7 MB per 65³ cube (274,625 lines). Round up slightly so the
        # "Large sync" warning triggers at roughly the intended threshold.
        per = 11 * 1024 * 1024 if size >= 65 else 1280 * 1024
        est = len(rows) * per
        if est < 500 * 1024 * 1024:
            return True
        dv = self.config.davinci_path or "/"
        try:
            free = shutil.disk_usage(os.path.dirname(dv) or "/").free
        except OSError:
            free = None
        low_disk = free is not None and free < est * 2
        msg = QMessageBox(self._main_window)
        msg.setWindowTitle("Large sync")
        msg.setIcon(QMessageBox.Icon.Warning if low_disk else QMessageBox.Icon.Question)
        def gb(n: int) -> str:
            return f"{n / (1024**3):.1f} GB" if n >= 1024**3 else f"{n / (1024**2):.0f} MB"
        text = (f"PassXMP will sync {len(rows)} presets.\n\n"
                f"At LUT size {size}³, this will write approximately {gb(est)}.")
        if low_disk:
            text += f"\n\n⚠︎ Free space is tight ({gb(free)})."
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Ok)
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        msg.button(QMessageBox.StandardButton.Ok).setText("Sync anyway")
        return msg.exec() == QMessageBox.StandardButton.Ok

    @pyqtSlot(bool)
    def _on_pause_toggled(self, now_paused: bool) -> None:
        if now_paused:
            self._stop_watcher()
        else:
            self._start_watcher()

    @pyqtSlot()
    def _on_tray_pause(self) -> None:
        self._on_pause_toggled(not self._is_paused)

    @pyqtSlot()
    def _on_tray_sync_all(self) -> None:
        self._registry.select_defaults()
        self._on_sync_requested(self._registry.selected_rows())

    @pyqtSlot()
    def _on_show_main(self) -> None:
        if self._main_window:
            self._main_window.show()
            self._main_window.raise_()
            self._main_window.activateWindow()

    @pyqtSlot()
    def _on_quit(self) -> None:
        # The joins inside _cancel_running_sync and _stop_watcher can block
        # the main thread for several seconds on slow filesystems. Hint at
        # what's happening before we freeze the UI.
        if self._main_window:
            self._main_window.setWindowTitle("PassXMP — Stopping…")
            QApplication.processEvents()
        self._cancel_running_sync()
        self._stop_watcher()
        QApplication.quit()
