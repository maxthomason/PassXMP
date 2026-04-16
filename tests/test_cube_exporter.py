"""Tests for .cube file exporter."""

import os
import tempfile

import numpy as np
import pytest

from src.core.cube_exporter import write_cube
from src.core.hald_generator import generate_hald_identity


class TestWriteCube:
    def test_basic_write(self, tmp_path):
        size = 5
        lut = generate_hald_identity(size)
        out = str(tmp_path / "test.cube")

        write_cube(lut, out, "Test LUT", size=size)

        assert os.path.exists(out)
        content = open(out).read()
        assert 'TITLE "Test LUT"' in content
        assert "LUT_3D_SIZE 5" in content
        assert "DOMAIN_MIN 0.0 0.0 0.0" in content
        assert "DOMAIN_MAX 1.0 1.0 1.0" in content

    def test_line_count(self, tmp_path):
        size = 5
        lut = generate_hald_identity(size)
        out = str(tmp_path / "test.cube")
        write_cube(lut, out, "Test", size=size)

        lines = open(out).readlines()
        # Header: TITLE, LUT_3D_SIZE, DOMAIN_MIN, DOMAIN_MAX, blank line = 5
        # Data: size^3 = 125
        data_lines = [l for l in lines if l.strip() and not l.startswith(("TITLE", "LUT", "DOMAIN"))]
        assert len(data_lines) == size ** 3

    def test_values_in_range(self, tmp_path):
        size = 5
        lut = generate_hald_identity(size)
        # Add some out-of-range values
        lut[0] = [-0.1, 1.2, 0.5]
        out = str(tmp_path / "test.cube")
        write_cube(lut, out, "Test", size=size)

        # Read back and verify clamping
        lines = open(out).readlines()
        for line in lines:
            line = line.strip()
            if line and not line.startswith(("TITLE", "LUT", "DOMAIN")):
                values = [float(v) for v in line.split()]
                for v in values:
                    assert 0.0 <= v <= 1.0

    def test_wrong_shape_raises(self, tmp_path):
        lut = np.zeros((10, 3), dtype=np.float32)
        out = str(tmp_path / "test.cube")
        with pytest.raises(ValueError, match="Expected LUT data shape"):
            write_cube(lut, out, "Bad", size=5)

    def test_roundtrip_identity(self, tmp_path):
        """Write and read back an identity LUT, verify values match."""
        size = 5
        lut = generate_hald_identity(size)
        out = str(tmp_path / "identity.cube")
        write_cube(lut, out, "Identity", size=size)

        # Read back
        read_data = []
        with open(out) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith(("TITLE", "LUT", "DOMAIN", "#")):
                    values = [float(v) for v in line.split()]
                    if len(values) == 3:
                        read_data.append(values)

        read_array = np.array(read_data, dtype=np.float32)
        np.testing.assert_allclose(read_array, lut, atol=1e-5)
