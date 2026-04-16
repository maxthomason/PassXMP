"""Smoke test: PassXMPApp boots, shows the window, both tabs work."""

from src.app import PassXMPApp


def test_app_starts_and_shows_empty_state(qapp, tmp_path):
    cfg_path = tmp_path / "config.json"
    app = PassXMPApp(config_path=str(cfg_path))
    app.start()
    try:
        win = app._main_window
        assert win is not None
        assert win.current_tab_name() == "Presets"
        presets = win.presets_view()
        # Summary should be renderable without crashing
        assert isinstance(presets.summary_text(), str)
        win.select_tab("Settings")
        assert win.current_tab_name() == "Settings"
    finally:
        # Skip QApplication.quit() — that would kill the session fixture.
        app._cancel_running_sync()
        app._stop_watcher()
