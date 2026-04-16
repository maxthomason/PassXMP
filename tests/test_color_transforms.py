"""Tests for color transformation pipeline."""

import numpy as np
import pytest

from src.core.hald_generator import generate_hald_identity
from src.core.color_transforms import (
    rgb_to_hsl, hsl_to_rgb,
    apply_white_balance, apply_saturation_vibrance,
    apply_hsl_adjustments, apply_tone_curve,
    apply_color_grading, apply_split_toning,
    apply_color_pipeline,
)


@pytest.fixture
def identity_small():
    """Small identity LUT for fast tests."""
    return generate_hald_identity(size=5)


@pytest.fixture
def neutral_params():
    """Parameters that should produce no change."""
    return {
        "Temperature": "5500",
        "Tint": "0",
        "Saturation": "0",
        "Vibrance": "0",
    }


class TestColorSpaceConversion:
    def test_rgb_to_hsl_black(self):
        rgb = np.array([[0.0, 0.0, 0.0]])
        hsl = rgb_to_hsl(rgb)
        assert hsl[0, 2] == pytest.approx(0.0, abs=1e-6)  # L = 0

    def test_rgb_to_hsl_white(self):
        rgb = np.array([[1.0, 1.0, 1.0]])
        hsl = rgb_to_hsl(rgb)
        assert hsl[0, 2] == pytest.approx(1.0, abs=1e-6)  # L = 1
        assert hsl[0, 1] == pytest.approx(0.0, abs=1e-6)  # S = 0

    def test_rgb_to_hsl_red(self):
        rgb = np.array([[1.0, 0.0, 0.0]])
        hsl = rgb_to_hsl(rgb)
        assert hsl[0, 0] == pytest.approx(0.0, abs=1e-6)  # H = 0
        assert hsl[0, 1] == pytest.approx(1.0, abs=1e-6)  # S = 1
        assert hsl[0, 2] == pytest.approx(0.5, abs=1e-6)  # L = 0.5

    def test_roundtrip(self):
        np.random.seed(42)
        rgb = np.random.rand(100, 3).astype(np.float32)
        hsl = rgb_to_hsl(rgb)
        rgb_back = hsl_to_rgb(hsl)
        np.testing.assert_allclose(rgb, rgb_back, atol=1e-5)


class TestHaldIdentity:
    def test_shape(self):
        identity = generate_hald_identity(size=5)
        assert identity.shape == (125, 3)

    def test_shape_33(self):
        identity = generate_hald_identity(size=33)
        assert identity.shape == (35937, 3)

    def test_range(self):
        identity = generate_hald_identity(size=10)
        assert identity.min() >= 0.0
        assert identity.max() <= 1.0

    def test_contains_black_and_white(self):
        identity = generate_hald_identity(size=5)
        # Should contain [0,0,0] and [1,1,1]
        assert np.any(np.all(identity == 0.0, axis=1))
        assert np.any(np.all(identity == 1.0, axis=1))


class TestWhiteBalance:
    def test_neutral_wb_no_change(self, identity_small, neutral_params):
        result = apply_white_balance(identity_small, neutral_params)
        np.testing.assert_allclose(result, identity_small, atol=1e-5)

    def test_warm_wb_shifts_warm(self, identity_small):
        params = {"Temperature": "7000", "Tint": "0"}
        result = apply_white_balance(identity_small, params)
        # Red channel should increase on average, blue decrease
        mid_gray = identity_small[identity_small[:, 0] == identity_small[:, 1]]
        if len(mid_gray) > 0:
            idx = np.where(np.all(identity_small == mid_gray[0], axis=1))[0][0]
            assert result[idx, 0] >= result[idx, 2]  # R >= B for warm

    def test_output_clamped(self, identity_small):
        params = {"Temperature": "10000", "Tint": "50"}
        result = apply_white_balance(identity_small, params)
        assert result.min() >= 0.0
        assert result.max() <= 1.0


class TestSaturationVibrance:
    def test_zero_no_change(self, identity_small, neutral_params):
        result = apply_saturation_vibrance(identity_small, neutral_params)
        np.testing.assert_allclose(result, identity_small, atol=1e-5)

    def test_positive_saturation_increases(self, identity_small):
        params = {"Saturation": "50", "Vibrance": "0"}
        result = apply_saturation_vibrance(identity_small, params)
        # Saturated colors should be more saturated
        hsl_before = rgb_to_hsl(identity_small)
        hsl_after = rgb_to_hsl(result)
        # Average saturation of non-gray pixels should increase
        mask = hsl_before[..., 1] > 0.1
        if np.any(mask):
            assert hsl_after[mask, 1].mean() > hsl_before[mask, 1].mean()

    def test_output_valid_range(self, identity_small):
        params = {"Saturation": "100", "Vibrance": "100"}
        result = apply_saturation_vibrance(identity_small, params)
        assert result.min() >= 0.0
        assert result.max() <= 1.0


class TestHSLAdjustments:
    def test_zero_no_change(self, identity_small):
        params = {f"HueAdjustment{c}": "0" for c in
                  ["Red", "Orange", "Yellow", "Green", "Aqua", "Blue", "Purple", "Magenta"]}
        result = apply_hsl_adjustments(identity_small, params)
        np.testing.assert_allclose(result, identity_small, atol=1e-5)

    def test_hue_shift_red(self, identity_small):
        params = {"HueAdjustmentRed": "30"}
        result = apply_hsl_adjustments(identity_small, params)
        # Result should differ from input
        assert not np.allclose(result, identity_small, atol=1e-3)

    def test_output_valid_range(self, identity_small):
        params = {
            "HueAdjustmentRed": "45",
            "SaturationAdjustmentGreen": "-50",
            "LuminanceAdjustmentBlue": "+30",
        }
        result = apply_hsl_adjustments(identity_small, params)
        assert result.min() >= 0.0
        assert result.max() <= 1.0


class TestToneCurve:
    def test_linear_no_change(self, identity_small):
        params = {"ToneCurveName2012": "Linear"}
        result = apply_tone_curve(identity_small, params)
        np.testing.assert_allclose(result, identity_small, atol=1e-5)

    def test_s_curve(self, identity_small):
        params = {
            "ToneCurvePV2012": ["0, 0", "64, 48", "128, 128", "192, 208", "255, 255"],
        }
        result = apply_tone_curve(identity_small, params)
        # S-curve should make darks darker and lights lighter
        assert not np.allclose(result, identity_small, atol=1e-3)

    def test_parametric_curve(self, identity_small):
        params = {
            "ParametricShadows": "20",
            "ParametricDarks": "10",
            "ParametricLights": "-10",
            "ParametricHighlights": "-20",
        }
        result = apply_tone_curve(identity_small, params)
        assert not np.allclose(result, identity_small, atol=1e-3)


class TestColorGrading:
    def test_zero_no_change(self, identity_small):
        params = {}
        result = apply_color_grading(identity_small, params)
        np.testing.assert_allclose(result, identity_small, atol=1e-5)

    def test_shadow_tint(self, identity_small):
        params = {
            "ColorGradeShadowHue": "220",
            "ColorGradeShadowSat": "50",
            "ColorGradeShadowLum": "0",
        }
        result = apply_color_grading(identity_small, params)
        assert not np.allclose(result, identity_small, atol=1e-3)

    def test_output_clamped(self, identity_small):
        params = {
            "ColorGradeShadowHue": "220",
            "ColorGradeShadowSat": "100",
            "ColorGradeHighlightHue": "40",
            "ColorGradeHighlightSat": "100",
        }
        result = apply_color_grading(identity_small, params)
        assert result.min() >= 0.0
        assert result.max() <= 1.0


class TestSplitToning:
    def test_zero_no_change(self, identity_small):
        params = {
            "SplitToningShadowSaturation": "0",
            "SplitToningHighlightSaturation": "0",
        }
        result = apply_split_toning(identity_small, params)
        np.testing.assert_allclose(result, identity_small, atol=1e-5)

    def test_warm_split_tone(self, identity_small):
        params = {
            "SplitToningShadowHue": "40",
            "SplitToningShadowSaturation": "30",
            "SplitToningHighlightHue": "50",
            "SplitToningHighlightSaturation": "20",
            "SplitToningBalance": "0",
        }
        result = apply_split_toning(identity_small, params)
        assert not np.allclose(result, identity_small, atol=1e-3)


class TestFullPipeline:
    def test_neutral_params_near_identity(self):
        identity = generate_hald_identity(size=5)
        params = {
            "Temperature": "5500", "Tint": "0",
            "Saturation": "0", "Vibrance": "0",
            "ToneCurveName2012": "Linear",
        }
        result = apply_color_pipeline(identity, params)
        np.testing.assert_allclose(result, identity, atol=1e-4)

    def test_complex_preset_output_valid(self):
        identity = generate_hald_identity(size=5)
        params = {
            "Temperature": "6200", "Tint": "+12",
            "Vibrance": "+25", "Saturation": "-10",
            "HueAdjustmentRed": "+5", "SaturationAdjustmentOrange": "+10",
            "LuminanceAdjustmentBlue": "-10",
            "SplitToningShadowHue": "40", "SplitToningShadowSaturation": "20",
            "SplitToningHighlightHue": "50", "SplitToningHighlightSaturation": "15",
        }
        result = apply_color_pipeline(identity, params)
        assert result.shape == identity.shape
        assert result.dtype == np.float32
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_pipeline_deterministic(self):
        identity = generate_hald_identity(size=5)
        params = {"Temperature": "6500", "Saturation": "+20"}
        r1 = apply_color_pipeline(identity, params)
        r2 = apply_color_pipeline(identity, params)
        np.testing.assert_array_equal(r1, r2)
