"""File system watcher for Lightroom preset folders using watchdog."""

import logging
import os
import threading
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from ..core.sync_engine import process_xmp_file
from .mirror import get_mirror_path, delete_cube_mirror, move_cube_mirror

logger = logging.getLogger("passxmp.watcher")


class XMPHandler(FileSystemEventHandler):
    """Handles .xmp file events and triggers the conversion pipeline."""

    def __init__(self, lr_root: str, dv_root: str, lut_size: int = 33,
                 on_sync: callable = None, on_event: callable = None):
        super().__init__()
        self.lr_root = lr_root
        self.dv_root = dv_root
        self.lut_size = lut_size
        self.on_sync = on_sync
        self.on_event = on_event
        self._debounce_timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def _is_xmp(self, path: str) -> bool:
        return path.lower().endswith(".xmp")

    def _debounce_process(self, xmp_path: str) -> None:
        """Debounce rapid file changes (e.g. editor save-then-rewrite)."""
        with self._lock:
            if xmp_path in self._debounce_timers:
                self._debounce_timers[xmp_path].cancel()
            timer = threading.Timer(0.5, self._do_process, args=[xmp_path])
            self._debounce_timers[xmp_path] = timer
            timer.start()

    def _do_process(self, xmp_path: str) -> None:
        with self._lock:
            self._debounce_timers.pop(xmp_path, None)

        cube_path = get_mirror_path(xmp_path, self.lr_root, self.dv_root)
        success = process_xmp_file(xmp_path, cube_path, self.lut_size)
        if success and self.on_sync:
            rel = os.path.relpath(xmp_path, self.lr_root)
            cube_rel = os.path.relpath(cube_path, self.dv_root)
            self.on_sync(rel, cube_rel)

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_xmp(event.src_path):
            logger.info("XMP created: %s", event.src_path)
            if self.on_event:
                self.on_event("created", event.src_path)
            self._debounce_process(event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_xmp(event.src_path):
            logger.info("XMP modified: %s", event.src_path)
            if self.on_event:
                self.on_event("modified", event.src_path)
            self._debounce_process(event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_xmp(event.src_path):
            logger.info("XMP deleted: %s", event.src_path)
            if self.on_event:
                self.on_event("deleted", event.src_path)
            delete_cube_mirror(event.src_path, self.lr_root, self.dv_root)

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_xmp(event.src_path):
            logger.info("XMP moved: %s -> %s", event.src_path, event.dest_path)
            if self.on_event:
                self.on_event("moved", event.src_path, event.dest_path)
            move_cube_mirror(event.src_path, event.dest_path,
                             self.lr_root, self.dv_root)


class FolderWatcher:
    """Manages the watchdog Observer for monitoring .xmp file changes."""

    def __init__(self, lr_root: str, dv_root: str, lut_size: int = 33,
                 on_sync: callable = None, on_event: callable = None):
        self.lr_root = lr_root
        self.dv_root = dv_root
        self.lut_size = lut_size
        self.on_sync = on_sync
        self.on_event = on_event
        self._observer: Observer | None = None
        self._handler: XMPHandler | None = None

    def start(self) -> None:
        """Start watching the Lightroom presets folder."""
        if self._observer is not None:
            self.stop()

        self._handler = XMPHandler(
            self.lr_root, self.dv_root, self.lut_size,
            self.on_sync, self.on_event,
        )
        self._observer = Observer()
        self._observer.schedule(self._handler, self.lr_root, recursive=True)
        self._observer.daemon = True
        self._observer.start()
        logger.info("Watching: %s", self.lr_root)

    def stop(self) -> None:
        """Stop the folder watcher."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            self._handler = None
            logger.info("Watcher stopped")

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()
