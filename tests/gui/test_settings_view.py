"""Tests for the Settings tab."""

from src.gui.settings_view import SettingsView


def test_settings_initial_state(qapp):
    view = SettingsView(
        lr_path="/lr", dv_path="/dv",
        lut_size=33, auto_start=True,
        default_lr="/default/lr", default_dv="/default/dv",
    )
    assert view.lr_path() == "/lr"
    assert view.dv_path() == "/dv"
    assert view.lut_size() == 33
    assert view.auto_start() is True


def test_settings_emits_config_changed_on_lut_size_flip(qapp, qtbot):
    view = SettingsView(lr_path="/lr", dv_path="/dv", lut_size=33, auto_start=True,
                        default_lr="", default_dv="")
    with qtbot.waitSignal(view.config_changed, timeout=500) as blocker:
        view._radio_65.setChecked(True)
    lr, dv, size, auto = blocker.args
    assert size == 65


def test_settings_emits_config_changed_on_auto_start_toggle(qapp, qtbot):
    view = SettingsView(lr_path="/lr", dv_path="/dv", lut_size=33, auto_start=True,
                        default_lr="", default_dv="")
    with qtbot.waitSignal(view.config_changed, timeout=500) as blocker:
        view._auto_start_cb.setChecked(False)
    _lr, _dv, _size, auto = blocker.args
    assert auto is False


def test_settings_watcher_dot_reflects_state(qapp):
    view = SettingsView(lr_path="/lr", dv_path="/dv", lut_size=33, auto_start=True,
                        default_lr="", default_dv="")
    view.set_watcher_running(True)
    assert view.watcher_dot().is_running() is True
    view.set_watcher_running(False)
    assert view.watcher_dot().is_running() is False
    assert view.watcher_button().text() == "Resume"


def test_settings_emits_pause_toggled(qapp, qtbot):
    view = SettingsView(lr_path="/lr", dv_path="/dv", lut_size=33, auto_start=True,
                        default_lr="", default_dv="")
    view.set_watcher_running(True)
    with qtbot.waitSignal(view.pause_toggled, timeout=500) as blocker:
        view.watcher_button().click()
    assert blocker.args == [True]  # now paused
