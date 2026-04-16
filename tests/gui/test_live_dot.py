"""Tests for the LiveDot widget."""

from src.gui.widgets.live_dot import LiveDot


def test_live_dot_default_is_running(qapp):
    dot = LiveDot()
    assert dot.is_running() is True
    assert dot.width() > 0
    assert dot.height() > 0


def test_live_dot_set_running_toggles_animation(qapp):
    dot = LiveDot()
    dot.set_running(False)
    assert dot.is_running() is False
    dot.set_running(True)
    assert dot.is_running() is True
