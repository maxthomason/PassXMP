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


from src.core.file_registry import FileRegistry


def test_registry_scan_finds_xmp_files():
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "a.xmp"), mtime=1000.0)
        _touch(os.path.join(lr, "VSCO", "b.xmp"), mtime=1000.0)
        _touch(os.path.join(lr, "VSCO", "Film", "c.xmp"), mtime=1000.0)
        # Non-xmp file should be skipped
        _touch(os.path.join(lr, "readme.txt"))

        registry = FileRegistry()
        registry.rescan(lr, dv)

        rows = registry.rows()
        assert len(rows) == 3
        paths_by_name = {os.path.basename(r.xmp_path): r.xmp_path for r in rows}
        assert "a.xmp" in paths_by_name
        assert paths_by_name["c.xmp"].endswith(os.path.join("VSCO", "Film", "c.xmp"))
        assert paths_by_name["b.xmp"].endswith(os.path.join("VSCO", "b.xmp"))


def test_registry_folder_is_top_level_subdir():
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "root.xmp"), mtime=1000.0)
        _touch(os.path.join(lr, "VSCO", "Film", "deep.xmp"), mtime=1000.0)

        registry = FileRegistry()
        registry.rescan(lr, dv)

        by_name = {os.path.basename(r.xmp_path): r for r in registry.rows()}
        assert by_name["root.xmp"].folder == ""
        assert by_name["deep.xmp"].folder == "VSCO"


def test_registry_populates_cube_mtime_when_present():
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "a.xmp"), mtime=1000.0)
        _touch(os.path.join(dv, "a.cube"), mtime=2000.0)

        registry = FileRegistry()
        registry.rescan(lr, dv)

        row = registry.rows()[0]
        assert row.cube_mtime == 2000.0


def test_registry_rescan_replaces_old_rows():
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "a.xmp"), mtime=1000.0)
        registry = FileRegistry()
        registry.rescan(lr, dv)
        assert len(registry.rows()) == 1

        os.remove(os.path.join(lr, "a.xmp"))
        _touch(os.path.join(lr, "b.xmp"), mtime=1000.0)
        registry.rescan(lr, dv)

        paths = [os.path.basename(r.xmp_path) for r in registry.rows()]
        assert paths == ["b.xmp"]


def test_registry_status_reflects_in_flight_set():
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        xmp = os.path.join(lr, "a.xmp")
        _touch(xmp, mtime=1000.0)

        registry = FileRegistry()
        registry.rescan(lr, dv)
        assert registry.status(xmp) == "pending"

        registry.mark_syncing(xmp)
        assert registry.status(xmp) == "syncing"


def test_registry_set_selected_updates_row():
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "a.xmp"), mtime=1000.0)
        registry = FileRegistry()
        registry.rescan(lr, dv)

        xmp = registry.rows()[0].xmp_path
        registry.set_selected(xmp, True)
        assert registry.rows()[0].selected is True

        registry.set_selected(xmp, False)
        assert registry.rows()[0].selected is False


def test_registry_select_defaults_checks_pending_and_failed():
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "pending.xmp"), mtime=1000.0)
        _touch(os.path.join(lr, "synced.xmp"), mtime=1000.0)
        _touch(os.path.join(dv, "synced.cube"), mtime=2000.0)

        registry = FileRegistry()
        registry.rescan(lr, dv)
        registry.select_defaults()

        by_name = {os.path.basename(r.xmp_path): r for r in registry.rows()}
        assert by_name["pending.xmp"].selected is True
        assert by_name["synced.xmp"].selected is False


def test_registry_selected_paths_round_trip():
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "a.xmp"), mtime=1000.0)
        _touch(os.path.join(lr, "b.xmp"), mtime=1000.0)
        registry = FileRegistry()
        registry.rescan(lr, dv)

        registry.restore_selection(["a.xmp"])
        by_name = {os.path.basename(r.xmp_path): r for r in registry.rows()}
        assert by_name["a.xmp"].selected is True
        assert by_name["b.xmp"].selected is False

        assert registry.selected_relative_paths() == ["a.xmp"]


def test_registry_on_watcher_created_inserts_row():
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        registry = FileRegistry()
        registry.rescan(lr, dv)
        assert registry.row_count() == 0

        new_xmp = os.path.join(lr, "new.xmp")
        _touch(new_xmp, mtime=1000.0)
        registry.on_watcher_created(new_xmp)

        assert registry.row_count() == 1
        assert registry.index_of(new_xmp) == 0


def test_registry_on_watcher_deleted_removes_row():
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        xmp = os.path.join(lr, "a.xmp")
        _touch(xmp, mtime=1000.0)
        registry = FileRegistry()
        registry.rescan(lr, dv)

        registry.on_watcher_deleted(xmp)
        assert registry.row_count() == 0
        assert registry.index_of(xmp) is None


def test_registry_on_watcher_modified_refreshes_mtimes():
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        xmp = os.path.join(lr, "a.xmp")
        _touch(xmp, mtime=1000.0)
        registry = FileRegistry()
        registry.rescan(lr, dv)
        assert registry.rows()[0].xmp_mtime == 1000.0

        os.utime(xmp, (3000.0, 3000.0))
        registry.on_watcher_modified(xmp)

        assert registry.rows()[0].xmp_mtime == 3000.0
