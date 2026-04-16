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

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[FileState] = []
        self._index: dict[str, int] = {}
        self._in_flight: set[str] = set()
        self._failed: set[str] = set()
        self._lr_root: str = ""
        self._dv_root: str = ""

    # ----- scanning -----

    def rescan(self, lr_root: str, dv_root: str) -> None:
        self._lr_root = lr_root
        self._dv_root = dv_root
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
        if ok:
            self._failed.discard(xmp_path)
            if idx is not None and os.path.exists(self._rows[idx].cube_path):
                self._rows[idx].cube_mtime = os.path.getmtime(self._rows[idx].cube_path)
                self._rows[idx].last_error = None
        else:
            self._failed.add(xmp_path)
            if idx is not None:
                self._rows[idx].last_error = err
        self._emit_changed(xmp_path)

    def _emit_changed(self, xmp_path: str) -> None:
        idx = self._index.get(xmp_path)
        if idx is not None:
            self.row_changed.emit(idx)
