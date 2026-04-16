"""Tests for path mirroring and sync logic."""

import os
import tempfile

import pytest

from src.watcher.mirror import get_mirror_path, delete_cube_mirror, move_cube_mirror, initial_sync


class TestGetMirrorPath:
    def test_simple_path(self):
        result = get_mirror_path(
            "/lr/presets/MyPreset.xmp",
            "/lr/presets",
            "/dv/lut",
        )
        assert result == "/dv/lut/MyPreset.cube"

    def test_nested_path(self):
        result = get_mirror_path(
            "/lr/presets/VSCO/Film/A4.xmp",
            "/lr/presets",
            "/dv/lut",
        )
        expected = os.path.join("/dv/lut", "VSCO", "Film", "A4.cube")
        assert result == expected

    def test_preserves_hierarchy(self):
        result = get_mirror_path(
            "/lr/presets/Wedding/Airy Light.xmp",
            "/lr/presets",
            "/dv/lut",
        )
        assert "Wedding" in result
        assert result.endswith("Airy Light.cube")


class TestDeleteCubeMirror:
    def test_deletes_existing(self, tmp_path):
        lr_root = str(tmp_path / "lr")
        dv_root = str(tmp_path / "dv")
        os.makedirs(lr_root)
        os.makedirs(dv_root)

        # Create a cube file
        cube_path = os.path.join(dv_root, "test.cube")
        with open(cube_path, "w") as f:
            f.write("test")

        xmp_path = os.path.join(lr_root, "test.xmp")
        result = delete_cube_mirror(xmp_path, lr_root, dv_root)
        assert result is True
        assert not os.path.exists(cube_path)

    def test_missing_cube_returns_false(self, tmp_path):
        lr_root = str(tmp_path / "lr")
        dv_root = str(tmp_path / "dv")
        os.makedirs(lr_root)
        os.makedirs(dv_root)

        xmp_path = os.path.join(lr_root, "nonexistent.xmp")
        result = delete_cube_mirror(xmp_path, lr_root, dv_root)
        assert result is False


class TestMoveCubeMirror:
    def test_move_file(self, tmp_path):
        lr_root = str(tmp_path / "lr")
        dv_root = str(tmp_path / "dv")
        os.makedirs(os.path.join(lr_root, "old"))
        os.makedirs(os.path.join(lr_root, "new"))
        os.makedirs(os.path.join(dv_root, "old"))

        # Create old cube
        old_cube = os.path.join(dv_root, "old", "preset.cube")
        with open(old_cube, "w") as f:
            f.write("cube data")

        old_xmp = os.path.join(lr_root, "old", "preset.xmp")
        new_xmp = os.path.join(lr_root, "new", "preset.xmp")

        result = move_cube_mirror(old_xmp, new_xmp, lr_root, dv_root)
        assert result is True
        assert not os.path.exists(old_cube)
        assert os.path.exists(os.path.join(dv_root, "new", "preset.cube"))


class TestInitialSync:
    def test_sync_creates_cubes(self, tmp_path):
        lr_root = str(tmp_path / "lr")
        dv_root = str(tmp_path / "dv")
        os.makedirs(lr_root)
        os.makedirs(dv_root)

        # Copy a fixture
        fixture = os.path.join(
            os.path.dirname(__file__), "fixtures", "sample_presets", "minimal.xmp"
        )
        import shutil
        shutil.copy(fixture, os.path.join(lr_root, "minimal.xmp"))

        converted, total = initial_sync(lr_root, dv_root, lut_size=5)

        assert total == 1
        assert converted == 1
        assert os.path.exists(os.path.join(dv_root, "minimal.cube"))

    def test_skips_existing_up_to_date(self, tmp_path):
        lr_root = str(tmp_path / "lr")
        dv_root = str(tmp_path / "dv")
        os.makedirs(lr_root)
        os.makedirs(dv_root)

        fixture = os.path.join(
            os.path.dirname(__file__), "fixtures", "sample_presets", "minimal.xmp"
        )
        import shutil
        shutil.copy(fixture, os.path.join(lr_root, "minimal.xmp"))

        # First sync
        initial_sync(lr_root, dv_root, lut_size=5)

        # Second sync should skip
        converted, total = initial_sync(lr_root, dv_root, lut_size=5)
        assert total == 1
        assert converted == 0  # Already up to date
