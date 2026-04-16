"""Tests for ProgressFooter idle/active swapping and button labels."""

from src.gui.widgets.progress_footer import ProgressFooter


def test_footer_defaults_to_idle(qapp):
    footer = ProgressFooter()
    assert footer.is_idle() is True


def test_footer_idle_button_label_reflects_selection(qapp):
    footer = ProgressFooter()
    footer.set_selection_count(0)
    assert footer.sync_button_label() == "Sync"
    assert footer.sync_button_enabled() is False

    footer.set_selection_count(12)
    assert footer.sync_button_label() == "Sync 12 selected"
    assert footer.sync_button_enabled() is True


def test_footer_set_active_switches_to_active_state(qapp):
    footer = ProgressFooter()
    footer.set_active(current_name="A4.xmp", folder="VSCO",
                      current_index=3, total=12, bytes_written=1_800_000)
    assert footer.is_idle() is False


def test_footer_set_idle_returns_to_idle(qapp):
    footer = ProgressFooter()
    footer.set_active(current_name="A4.xmp", folder="VSCO",
                      current_index=1, total=2, bytes_written=0)
    footer.set_idle(last_sync_iso=None, selected_count=0)
    assert footer.is_idle() is True


def test_footer_emits_sync_clicked(qapp, qtbot):
    footer = ProgressFooter()
    footer.set_selection_count(3)
    with qtbot.waitSignal(footer.sync_clicked, timeout=500):
        footer.sync_button().click()


def test_footer_emits_stop_clicked(qapp, qtbot):
    footer = ProgressFooter()
    footer.set_active(current_name="A4.xmp", folder="VSCO",
                      current_index=1, total=2, bytes_written=0)
    with qtbot.waitSignal(footer.stop_clicked, timeout=500):
        footer.stop_button().click()
