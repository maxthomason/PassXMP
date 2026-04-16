"""Tests for XMP parsing and sanitization."""

import os
import pytest

from src.core.xmp_parser import parse_xmp, sanitize, COLOR_SAFE_PARAMS, ZEROED_PARAMS

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "sample_presets")


class TestParseXmp:
    def test_parse_warm_film(self):
        params = parse_xmp(os.path.join(FIXTURES, "warm_film.xmp"))
        assert params["Temperature"] == "6200"
        assert params["Tint"] == "+12"
        assert params["Vibrance"] == "+25"
        assert params["Saturation"] == "-10"
        assert params["Exposure2012"] == "+0.50"
        assert params["HueAdjustmentRed"] == "+5"
        assert params["SplitToningShadowHue"] == "40"

    def test_parse_minimal(self):
        params = parse_xmp(os.path.join(FIXTURES, "minimal.xmp"))
        assert params["Temperature"] == "5500"
        assert params["Saturation"] == "+20"
        assert params["Vibrance"] == "+10"

    def test_parse_color_grading(self):
        params = parse_xmp(os.path.join(FIXTURES, "color_grading.xmp"))
        assert params["ColorGradeShadowHue"] == "220"
        assert params["ColorGradeShadowSat"] == "30"
        assert params["ColorGradeHighlightSat"] == "25"

    def test_parse_tone_curve_list(self):
        params = parse_xmp(os.path.join(FIXTURES, "warm_film.xmp"))
        curve = params.get("ToneCurvePV2012")
        assert isinstance(curve, list)
        assert len(curve) == 5
        assert curve[0] == "0, 0"

    def test_parse_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            parse_xmp("/nonexistent/file.xmp")


class TestSanitize:
    def test_color_safe_params_preserved(self):
        params = {"Temperature": "6200", "Vibrance": "+25", "Saturation": "-10"}
        result = sanitize(params)
        assert result["Temperature"] == "6200"
        assert result["Vibrance"] == "+25"
        assert result["Saturation"] == "-10"

    def test_zeroed_params(self):
        params = {
            "Exposure2012": "+0.50",
            "Contrast2012": "+10",
            "Clarity2012": "+15",
            "Sharpness": "40",
        }
        result = sanitize(params)
        assert result["Exposure2012"] == "0"
        assert result["Contrast2012"] == "0"
        assert result["Clarity2012"] == "0"
        assert result["Sharpness"] == "0"

    def test_mixed_params(self):
        params = {
            "Temperature": "6200",
            "Exposure2012": "+0.50",
            "HueAdjustmentRed": "+5",
            "Clarity2012": "+15",
        }
        result = sanitize(params)
        assert result["Temperature"] == "6200"
        assert result["Exposure2012"] == "0"
        assert result["HueAdjustmentRed"] == "+5"
        assert result["Clarity2012"] == "0"

    def test_full_preset_sanitize(self):
        params = parse_xmp(os.path.join(FIXTURES, "warm_film.xmp"))
        result = sanitize(params)
        # Color params preserved
        assert result["Temperature"] == "6200"
        assert result["Vibrance"] == "+25"
        # Non-color params zeroed
        assert result["Exposure2012"] == "0"
        assert result["Clarity2012"] == "0"
        assert result["Sharpness"] == "0"

    def test_tone_curve_list_preserved(self):
        params = parse_xmp(os.path.join(FIXTURES, "warm_film.xmp"))
        result = sanitize(params)
        curve = result.get("ToneCurvePV2012")
        assert isinstance(curve, list)
        assert len(curve) == 5


class TestXmpHardening:
    """Regression tests for malicious XMP payloads."""

    def test_billion_laughs_rejected(self, tmp_path):
        """defusedxml should refuse a file with nested entity definitions."""
        from defusedxml.common import EntitiesForbidden

        bomb = tmp_path / "bomb.xmp"
        bomb.write_text(
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE lolz [\n'
            ' <!ENTITY lol "lol">\n'
            ' <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">\n'
            ' <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">\n'
            ']>\n'
            '<x:xmpmeta xmlns:x="adobe:ns:meta/">&lol3;</x:xmpmeta>\n'
        )
        with pytest.raises(EntitiesForbidden):
            parse_xmp(str(bomb))

    def test_external_entity_rejected(self, tmp_path):
        """defusedxml should refuse SYSTEM entity references to local files."""
        from defusedxml.common import EntitiesForbidden

        evil = tmp_path / "evil.xmp"
        evil.write_text(
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>\n'
            '<x:xmpmeta xmlns:x="adobe:ns:meta/">&xxe;</x:xmpmeta>\n'
        )
        with pytest.raises(EntitiesForbidden):
            parse_xmp(str(evil))

    def test_process_xmp_file_survives_entity_bomb(self, tmp_path):
        """Full pipeline returns False without raising when fed a bomb."""
        from src.core.sync_engine import process_xmp_file

        bomb = tmp_path / "bomb.xmp"
        bomb.write_text(
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE lolz [<!ENTITY lol "lol">]>\n'
            '<x:xmpmeta xmlns:x="adobe:ns:meta/">&lol;</x:xmpmeta>\n'
        )
        cube = tmp_path / "bomb.cube"
        assert process_xmp_file(str(bomb), str(cube), lut_size=33) is False
        assert not cube.exists()
