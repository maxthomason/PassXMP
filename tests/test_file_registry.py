"""Tests for FileState status derivation."""

import os
import tempfile
import time

from src.core.file_registry import FileState, derive_status


def _touch(path: str, mtime: float | None = None) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("x")
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def test_derive_status_pending_when_no_cube():
    with tempfile.TemporaryDirectory() as d:
        xmp = os.path.join(d, "a.xmp")
        cube = os.path.join(d, "a.cube")
        _touch(xmp)
        state = FileState(xmp_path=xmp, cube_path=cube, folder="",
                          xmp_mtime=os.path.getmtime(xmp), cube_mtime=None)
        assert derive_status(state, in_flight=set(), failed=set()) == "pending"


def test_derive_status_synced_when_cube_newer():
    with tempfile.TemporaryDirectory() as d:
        xmp = os.path.join(d, "a.xmp")
        cube = os.path.join(d, "a.cube")
        _touch(xmp, mtime=1000.0)
        _touch(cube, mtime=2000.0)
        state = FileState(xmp_path=xmp, cube_path=cube, folder="",
                          xmp_mtime=1000.0, cube_mtime=2000.0)
        assert derive_status(state, in_flight=set(), failed=set()) == "synced"


def test_derive_status_pending_when_xmp_newer():
    with tempfile.TemporaryDirectory() as d:
        xmp = os.path.join(d, "a.xmp")
        cube = os.path.join(d, "a.cube")
        _touch(xmp, mtime=2000.0)
        _touch(cube, mtime=1000.0)
        state = FileState(xmp_path=xmp, cube_path=cube, folder="",
                          xmp_mtime=2000.0, cube_mtime=1000.0)
        assert derive_status(state, in_flight=set(), failed=set()) == "pending"


def test_derive_status_syncing_when_in_flight():
    state = FileState(xmp_path="/x/a.xmp", cube_path="/x/a.cube", folder="",
                      xmp_mtime=0.0, cube_mtime=None)
    assert derive_status(state, in_flight={"/x/a.xmp"}, failed=set()) == "syncing"


def test_derive_status_failed_wins_over_pending():
    state = FileState(xmp_path="/x/a.xmp", cube_path="/x/a.cube", folder="",
                      xmp_mtime=0.0, cube_mtime=None)
    assert derive_status(state, in_flight=set(), failed={"/x/a.xmp"}) == "failed"


def test_derive_status_syncing_wins_over_failed():
    state = FileState(xmp_path="/x/a.xmp", cube_path="/x/a.cube", folder="",
                      xmp_mtime=0.0, cube_mtime=None)
    assert derive_status(state, in_flight={"/x/a.xmp"},
                         failed={"/x/a.xmp"}) == "syncing"
