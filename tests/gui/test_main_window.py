"""Tests for the new MainWindow shell."""

from src.core.file_registry import FileRegistry
from src.gui.main_window import MainWindow


def test_main_window_has_two_tabs(qapp):
    reg = FileRegistry()
    win = MainWindow(
        registry=reg,
        lr_path="", dv_path="", lut_size=33, auto_start=True,
        default_lr="", default_dv="",
    )
    assert win.segmented_control().buttons().__len__() == 2
    assert win.current_tab_name() == "Presets"


def test_main_window_switches_tabs(qapp):
    reg = FileRegistry()
    win = MainWindow(
        registry=reg,
        lr_path="", dv_path="", lut_size=33, auto_start=True,
        default_lr="", default_dv="",
    )
    win.select_tab("Settings")
    assert win.current_tab_name() == "Settings"
    win.select_tab("Presets")
    assert win.current_tab_name() == "Presets"


def test_main_window_presets_view_is_backed_by_registry(qapp):
    reg = FileRegistry()
    win = MainWindow(
        registry=reg, lr_path="", dv_path="", lut_size=33, auto_start=True,
        default_lr="", default_dv="",
    )
    assert win.presets_view().visible_row_count() == 0
