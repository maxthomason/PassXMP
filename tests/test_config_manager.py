"""Tests for ConfigManager extensions."""

import json
import os
import tempfile

from src.config.config_manager import ConfigManager


def test_selected_relative_paths_defaults_empty():
    with tempfile.TemporaryDirectory() as d:
        cfg = ConfigManager(os.path.join(d, "c.json"))
        assert cfg.selected_relative_paths == []


def test_selected_relative_paths_round_trip():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "c.json")
        cfg = ConfigManager(path)
        cfg.selected_relative_paths = ["VSCO/A4.xmp", "Custom/Warm.xmp"]
        cfg.save()

        cfg2 = ConfigManager(path)
        assert cfg2.selected_relative_paths == ["VSCO/A4.xmp", "Custom/Warm.xmp"]


def test_selected_relative_paths_normalises_to_list():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "c.json")
        with open(path, "w") as f:
            json.dump({"selected_relative_paths": None}, f)
        cfg = ConfigManager(path)
        assert cfg.selected_relative_paths == []


def test_save_is_atomic_no_temp_left(tmp_path):
    from src.config.config_manager import ConfigManager
    path = tmp_path / "c.json"
    cfg = ConfigManager(str(path))
    cfg.lightroom_path = "/x"
    cfg.save()

    assert path.exists()
    assert not (tmp_path / "c.json.tmp").exists()


def test_save_cleans_up_temp_on_failure(tmp_path, monkeypatch):
    import os as _os
    import pytest as _pytest
    from src.config.config_manager import ConfigManager

    path = tmp_path / "c.json"
    cfg = ConfigManager(str(path))
    cfg.lightroom_path = "/x"

    def boom(src, dst):
        raise RuntimeError("simulated rename failure")

    monkeypatch.setattr(_os, "replace", boom)
    with _pytest.raises(RuntimeError):
        cfg.save()

    assert not path.exists(), "main config must not be overwritten"
    assert not (tmp_path / "c.json.tmp").exists(), "temp must be cleaned up"
