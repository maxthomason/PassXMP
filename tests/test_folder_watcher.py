"""Tests for FolderWatcher event callbacks."""

import os
import tempfile
import time

import pytest

from src.watcher.folder_watcher import FolderWatcher


def _touch(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("dummy")


def _wait(predicate, timeout=3.0, interval=0.05):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def test_watcher_fires_on_event_created(tmp_path):
    lr = tmp_path / "lr"; dv = tmp_path / "dv"
    lr.mkdir(); dv.mkdir()
    events: list[tuple[str, str]] = []

    w = FolderWatcher(
        str(lr), str(dv), 33,
        on_sync=lambda _a, _b: None,
        on_event=lambda kind, path, _new=None: events.append((kind, path)),
    )
    w.start()
    try:
        target = lr / "a.xmp"
        _touch(str(target))
        assert _wait(lambda: any(k == "created" and p == str(target) for k, p in events)), events
    finally:
        w.stop()


def test_watcher_fires_on_event_deleted(tmp_path):
    lr = tmp_path / "lr"; dv = tmp_path / "dv"
    lr.mkdir(); dv.mkdir()
    target = lr / "a.xmp"
    _touch(str(target))
    events: list[tuple[str, str]] = []

    w = FolderWatcher(
        str(lr), str(dv), 33,
        on_sync=lambda _a, _b: None,
        on_event=lambda kind, path, _new=None: events.append((kind, path)),
    )
    w.start()
    try:
        os.remove(str(target))
        assert _wait(lambda: any(k == "deleted" and p == str(target) for k, p in events)), events
    finally:
        w.stop()
