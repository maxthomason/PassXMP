"""Tests for the StatusCellDelegate painter behavior."""

from PyQt6.QtCore import Qt
from src.gui.widgets.status_cell import status_display, STATUS_COLORS


def test_status_display_synced():
    glyph, color_role = status_display("synced")
    assert glyph == "✓"
    assert color_role == "ok"


def test_status_display_failed():
    glyph, color_role = status_display("failed")
    assert glyph == "!"
    assert color_role == "fail"


def test_status_display_pending_is_blank():
    glyph, color_role = status_display("pending")
    assert glyph == ""
    assert color_role == "muted"


def test_status_display_syncing_is_blank_in_status_column():
    glyph, color_role = status_display("syncing")
    assert glyph == ""
    assert color_role == "muted"


def test_status_colors_has_all_roles():
    assert "ok" in STATUS_COLORS
    assert "fail" in STATUS_COLORS
    assert "muted" in STATUS_COLORS
