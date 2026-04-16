"""Canonical per-.xmp file state and the registry that owns it."""

from dataclasses import dataclass, field
from typing import Literal

Status = Literal["synced", "pending", "syncing", "failed"]


@dataclass
class FileState:
    xmp_path: str
    cube_path: str
    folder: str
    xmp_mtime: float
    cube_mtime: float | None = None
    selected: bool = False
    last_error: str | None = None


def derive_status(
    state: FileState,
    in_flight: set[str],
    failed: set[str],
) -> Status:
    """Compute the visible status from raw state + in-flight/failed sets.

    Order matters: syncing > failed > synced > pending.
    """
    if state.xmp_path in in_flight:
        return "syncing"
    if state.xmp_path in failed:
        return "failed"
    if state.cube_mtime is not None and state.cube_mtime >= state.xmp_mtime:
        return "synced"
    return "pending"


import os

from PyQt6.QtCore import QObject, pyqtSignal

from ..watcher.mirror import get_mirror_path


def _top_folder(xmp_path: str, lr_root: str) -> str:
    rel = os.path.relpath(xmp_path, lr_root)
    head = rel.split(os.sep, 1)[0]
    return "" if head == os.path.basename(rel) else head


class FileRegistry(QObject):
    """Owns the list of discovered .xmp files + their derived status.

    UI widgets subscribe to `rows_reset` / `row_changed` for updates. The
    registry holds no Qt widgets; it is a model.
    """

    rows_reset = pyqtSignal()
    row_changed = pyqtSignal(int)
    row_inserted = pyqtSignal(int)
    row_removed = pyqtSignal(int)
    scan_error = pyqtSignal(str)  # emitted when rescan can't read lr_root

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[FileState] = []
        self._index: dict[str, int] = {}
        self._in_flight: set[str] = set()
        self._failed: set[str] = set()
        self._lr_root: str = ""
        self._dv_root: str = ""
        self._last_scan_error: str = ""

    # ----- scanning -----

    def rescan(self, lr_root: str, dv_root: str) -> None:
        """Walk ``lr_root`` and rebuild the list of discovered .xmp files.

        Symlinks inside ``lr_root`` are NOT followed (``os.walk`` default).
        This is intentional — it keeps a crafted symlink from sending the
        scan off to `/etc` or a network share. A user who organises presets
        through symlinks will need to either flatten them into the folder
        or use a new configurable flag (not yet implemented).
        """
        self._lr_root = lr_root
        self._dv_root = dv_root
        self._last_scan_error = ""

        if lr_root and not os.path.isdir(lr_root):
            self._last_scan_error = f"Lightroom folder not found: {lr_root}"
        elif lr_root and not os.access(lr_root, os.R_OK):
            self._last_scan_error = f"Lightroom folder is not readable: {lr_root}"

        if self._last_scan_error:
            self._rows = []
            self._index = {}
            self._failed.clear()
            self.rows_reset.emit()
            self.scan_error.emit(self._last_scan_error)
            return

        rows: list[FileState] = []
        for dirpath, _dn, filenames in os.walk(lr_root):
            for fn in filenames:
                if not fn.lower().endswith(".xmp"):
                    continue
                xmp = os.path.join(dirpath, fn)
                cube = get_mirror_path(xmp, lr_root, dv_root)
                try:
                    xmtime = os.path.getmtime(xmp)
                except OSError:
                    continue
                cmtime = os.path.getmtime(cube) if os.path.exists(cube) else None
                rows.append(FileState(
                    xmp_path=xmp,
                    cube_path=cube,
                    folder=_top_folder(xmp, lr_root),
                    xmp_mtime=xmtime,
                    cube_mtime=cmtime,
                ))
        rows.sort(key=lambda r: (r.folder, os.path.basename(r.xmp_path).lower()))
        self._rows = rows
        self._index = {r.xmp_path: i for i, r in enumerate(rows)}
        self._failed.clear()  # stale errors don't survive a rescan
        self.rows_reset.emit()

    def last_scan_error(self) -> str:
        """Return the last rescan error message, or empty if the scan succeeded."""
        return self._last_scan_error

    # ----- queries -----

    def rows(self) -> list[FileState]:
        return list(self._rows)

    def row_count(self) -> int:
        return len(self._rows)

    def row_at(self, index: int) -> FileState:
        return self._rows[index]

    def index_of(self, xmp_path: str) -> int | None:
        return self._index.get(xmp_path)

    def status(self, xmp_path: str) -> Status:
        idx = self._index.get(xmp_path)
        if idx is None:
            return "pending"
        return derive_status(self._rows[idx], self._in_flight, self._failed)

    # ----- mutations -----

    def mark_syncing(self, xmp_path: str) -> None:
        self._in_flight.add(xmp_path)
        self._failed.discard(xmp_path)
        self._emit_changed(xmp_path)

    def mark_done(self, xmp_path: str, ok: bool, err: str | None = None) -> None:
        self._in_flight.discard(xmp_path)
        idx = self._index.get(xmp_path)
        if idx is None:
            # Row was removed (e.g. the watcher saw a delete event while
            # this file was still in flight). Drop the completion on the
            # floor so we don't leak the path in self._failed.
            self._failed.discard(xmp_path)
            return
        if ok:
            self._failed.discard(xmp_path)
            if os.path.exists(self._rows[idx].cube_path):
                self._rows[idx].cube_mtime = os.path.getmtime(self._rows[idx].cube_path)
                self._rows[idx].last_error = None
        else:
            self._failed.add(xmp_path)
            self._rows[idx].last_error = err
        self._emit_changed(xmp_path)

    def _emit_changed(self, xmp_path: str) -> None:
        idx = self._index.get(xmp_path)
        if idx is not None:
            self.row_changed.emit(idx)

    # ----- selection -----

    def set_selected(self, xmp_path: str, value: bool) -> None:
        idx = self._index.get(xmp_path)
        if idx is None:
            return
        if self._rows[idx].selected == value:
            return
        self._rows[idx].selected = value
        self.row_changed.emit(idx)

    def select_defaults(self) -> None:
        """Check every row whose derived status is pending or failed."""
        for row in self._rows:
            status = derive_status(row, self._in_flight, self._failed)
            target = status in ("pending", "failed")
            if row.selected != target:
                row.selected = target
        self.rows_reset.emit()

    def restore_selection(self, relative_paths: list[str]) -> None:
        targets = set(relative_paths)
        for row in self._rows:
            rel = os.path.relpath(row.xmp_path, self._lr_root) if self._lr_root else row.xmp_path
            row.selected = rel in targets
        self.rows_reset.emit()

    def selected_relative_paths(self) -> list[str]:
        out: list[str] = []
        for row in self._rows:
            if not row.selected:
                continue
            rel = os.path.relpath(row.xmp_path, self._lr_root) if self._lr_root else row.xmp_path
            out.append(rel)
        return out

    def selected_rows(self) -> list[FileState]:
        return [r for r in self._rows if r.selected]

    # ----- watcher integration -----

    def on_watcher_created(self, xmp_path: str) -> None:
        if xmp_path in self._index or not self._lr_root:
            return
        cube = get_mirror_path(xmp_path, self._lr_root, self._dv_root)
        try:
            xmtime = os.path.getmtime(xmp_path)
        except OSError:
            return
        cmtime = os.path.getmtime(cube) if os.path.exists(cube) else None
        state = FileState(
            xmp_path=xmp_path,
            cube_path=cube,
            folder=_top_folder(xmp_path, self._lr_root),
            xmp_mtime=xmtime,
            cube_mtime=cmtime,
        )
        idx = len(self._rows)
        self._rows.append(state)
        self._index[xmp_path] = idx
        self.row_inserted.emit(idx)

    def on_watcher_modified(self, xmp_path: str) -> None:
        idx = self._index.get(xmp_path)
        if idx is None:
            return
        row = self._rows[idx]
        try:
            row.xmp_mtime = os.path.getmtime(xmp_path)
        except OSError:
            return
        if os.path.exists(row.cube_path):
            row.cube_mtime = os.path.getmtime(row.cube_path)
        self._failed.discard(xmp_path)
        self.row_changed.emit(idx)

    def on_watcher_deleted(self, xmp_path: str) -> None:
        idx = self._index.pop(xmp_path, None)
        if idx is None:
            return
        self._rows.pop(idx)
        for i in range(idx, len(self._rows)):
            self._index[self._rows[i].xmp_path] = i
        self._in_flight.discard(xmp_path)
        self._failed.discard(xmp_path)
        self.row_removed.emit(idx)
