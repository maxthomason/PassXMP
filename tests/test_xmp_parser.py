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
