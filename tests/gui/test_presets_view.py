"""Tests for PresetsView — model columns, selection, search filtering."""

import os
import tempfile

from PyQt6.QtCore import Qt

from src.core.file_registry import FileRegistry
from src.gui.presets_view import PresetsView, PresetsTableModel


def _touch(path: str, mtime: float | None = None) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("x")
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def test_model_columns(qapp):
    reg = FileRegistry()
    model = PresetsTableModel(reg)
    assert model.columnCount() == 4  # check, name, folder, status


def test_model_row_count_matches_registry(qapp):
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "a.xmp"), mtime=1000.0)
        _touch(os.path.join(lr, "b.xmp"), mtime=1000.0)
        reg = FileRegistry()
        reg.rescan(lr, dv)
        model = PresetsTableModel(reg)
        assert model.rowCount() == 2


def test_model_checkbox_toggle_sets_selection(qapp):
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "a.xmp"), mtime=1000.0)
        reg = FileRegistry()
        reg.rescan(lr, dv)
        model = PresetsTableModel(reg)

        idx = model.index(0, 0)
        model.setData(idx, Qt.CheckState.Checked.value, Qt.ItemDataRole.CheckStateRole)
        assert reg.rows()[0].selected is True


def test_presets_view_search_filters_rows(qapp):
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "apple.xmp"), mtime=1000.0)
        _touch(os.path.join(lr, "banana.xmp"), mtime=1000.0)
        reg = FileRegistry()
        reg.rescan(lr, dv)
        view = PresetsView(reg)

        assert view.visible_row_count() == 2
        view.set_search_text("app")
        assert view.visible_row_count() == 1
        view.set_search_text("")
        assert view.visible_row_count() == 2


def test_presets_view_toggle_all_toggles_filtered_rows(qapp):
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "apple.xmp"), mtime=1000.0)
        _touch(os.path.join(lr, "banana.xmp"), mtime=1000.0)
        reg = FileRegistry()
        reg.rescan(lr, dv)
        view = PresetsView(reg)

        view.set_search_text("app")
        view.toggle_all_visible(True)
        by_name = {os.path.basename(r.xmp_path): r for r in reg.rows()}
        assert by_name["apple.xmp"].selected is True
        assert by_name["banana.xmp"].selected is False  # filtered out

        view.set_search_text("")
        view.toggle_all_visible(True)
        assert all(r.selected for r in reg.rows())


def test_presets_view_summary_label(qapp):
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "a.xmp"), mtime=1000.0)
        _touch(os.path.join(lr, "b.xmp"), mtime=1000.0)
        reg = FileRegistry()
        reg.rescan(lr, dv)
        view = PresetsView(reg)

        reg.set_selected(reg.rows()[0].xmp_path, True)
        assert "2 presets" in view.summary_text()
        assert "1 selected" in view.summary_text()


def test_empty_state_no_folders(qapp):
    reg = FileRegistry()
    view = PresetsView(reg)
    view.set_folders_configured(False)
    assert view.empty_state_visible() is True
    assert "Settings" in view.empty_state_text()


def test_empty_state_no_xmp_found(qapp):
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        reg = FileRegistry()
        reg.rescan(lr, dv)
        view = PresetsView(reg)
        view.set_folders_configured(True)
        assert view.empty_state_visible() is True
        assert "No Lightroom presets" in view.empty_state_text()


def test_empty_state_hidden_when_rows_exist(qapp):
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "a.xmp"), mtime=1000.0)
        reg = FileRegistry()
        reg.rescan(lr, dv)
        view = PresetsView(reg)
        view.set_folders_configured(True)
        assert view.empty_state_visible() is False


def test_context_menu_actions_for_synced_row(qapp):
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "a.xmp"), mtime=1000.0)
        _touch(os.path.join(dv, "a.cube"), mtime=2000.0)
        reg = FileRegistry()
        reg.rescan(lr, dv)
        view = PresetsView(reg)
        actions = [a.text() for a in view.context_menu_actions_for_row(0)]
        assert "Reveal .xmp in Finder" in actions
        assert "Reveal .cube in Finder" in actions
        assert "Resync this file" in actions


def test_context_menu_actions_for_failed_row(qapp):
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "a.xmp"), mtime=1000.0)
        reg = FileRegistry()
        reg.rescan(lr, dv)
        reg.mark_done(reg.rows()[0].xmp_path, ok=False, err="boom")
        view = PresetsView(reg)
        actions = [a.text() for a in view.context_menu_actions_for_row(0)]
        assert "Retry" in actions
        assert "Copy error message" in actions
        assert "Reveal .xmp in Finder" in actions


def test_context_menu_actions_for_pending_row(qapp):
    with tempfile.TemporaryDirectory() as lr, tempfile.TemporaryDirectory() as dv:
        _touch(os.path.join(lr, "a.xmp"), mtime=1000.0)
        reg = FileRegistry()
        reg.rescan(lr, dv)
        view = PresetsView(reg)
        actions = [a.text() for a in view.context_menu_actions_for_row(0)]
        assert "Reveal .xmp in Finder" in actions
        # Pending rows get only reveal; no resync/retry etc
        assert "Retry" not in actions
        assert "Resync this file" not in actions
