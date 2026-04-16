"""Color transformation pipeline for Lightroom XMP parameters.

Applies color transforms to a Hald CLUT identity array to produce
a 3D LUT encoding the Lightroom preset's color adjustments.

Transform order (matches Lightroom's internal pipeline):
1. White Balance (Temperature + Tint)
2. Global Saturation / Vibrance
3. HSL adjustments (per-channel hue, saturation, luminance)
4. Tone Curve (parametric + point curves)
5. Color Grading wheels (shadow/mid/highlight)
6. Split Toning (legacy presets)
"""

import numpy as np
from scipy.interpolate import CubicSpline


# --- Color space conversion utilities ---

def rgb_to_hsl(rgb: np.ndarray) -> np.ndarray:
    """Convert RGB array to HSL. Input/output shape: (..., 3), range 0-1."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    diff = max_c - min_c

    # Luminance
    l = (max_c + min_c) / 2.0

    # Saturation
    s = np.where(diff == 0, 0.0,
                 np.where(l <= 0.5,
                          diff / (max_c + min_c + 1e-10),
                          diff / (2.0 - max_c - min_c + 1e-10)))

    # Hue
    h = np.zeros_like(l)
    mask_r = (max_c == r) & (diff > 0)
    mask_g = (max_c == g) & (diff > 0) & ~mask_r
    mask_b = (max_c == b) & (diff > 0) & ~mask_r & ~mask_g

    h[mask_r] = (60.0 * ((g[mask_r] - b[mask_r]) / (diff[mask_r] + 1e-10))) % 360
    h[mask_g] = 60.0 * ((b[mask_g] - r[mask_g]) / (diff[mask_g] + 1e-10)) + 120.0
    h[mask_b] = 60.0 * ((r[mask_b] - g[mask_b]) / (diff[mask_b] + 1e-10)) + 240.0
    h = h % 360.0

    return np.stack([h, s, l], axis=-1)


def hsl_to_rgb(hsl: np.ndarray) -> np.ndarray:
    """Convert HSL array to RGB. Input/output shape: (..., 3).
    H in [0, 360], S and L in [0, 1].
    """
    h, s, l = hsl[..., 0], hsl[..., 1], hsl[..., 2]

    c = (1.0 - np.abs(2.0 * l - 1.0)) * s
    h_prime = (h / 60.0) % 6.0
    x = c * (1.0 - np.abs(h_prime % 2.0 - 1.0))
    m = l - c / 2.0

    r = np.zeros_like(h)
    g = np.zeros_like(h)
    b = np.zeros_like(h)

    idx = (h_prime >= 0) & (h_prime < 1)
    r[idx], g[idx], b[idx] = c[idx], x[idx], 0
    idx = (h_prime >= 1) & (h_prime < 2)
    r[idx], g[idx], b[idx] = x[idx], c[idx], 0
    idx = (h_prime >= 2) & (h_prime < 3)
    r[idx], g[idx], b[idx] = 0, c[idx], x[idx]
    idx = (h_prime >= 3) & (h_prime < 4)
    r[idx], g[idx], b[idx] = 0, x[idx], c[idx]
    idx = (h_prime >= 4) & (h_prime < 5)
    r[idx], g[idx], b[idx] = x[idx], 0, c[idx]
    idx = (h_prime >= 5) & (h_prime < 6)
    r[idx], g[idx], b[idx] = c[idx], 0, x[idx]

    return np.clip(np.stack([r + m, g + m, b + m], axis=-1), 0.0, 1.0)


# --- Lightroom hue range definitions ---

# Lightroom's 8 hue ranges with center hues and approximate widths (degrees).
# Ranges overlap for smooth blending.
LR_HUE_RANGES = {
    "Red":     (0,   30),
    "Orange":  (30,  60),
    "Yellow":  (60,  90),
    "Green":   (120, 60),
    "Aqua":    (180, 40),
    "Blue":    (220, 40),
    "Purple":  (270, 40),
    "Magenta": (310, 40),
}


def _hue_weight(hue: np.ndarray, center: float, width: float) -> np.ndarray:
    """Compute smooth blending weight for a hue range.

    Uses a cosine-based falloff centered at `center` with the given `width`.
    """
    diff = (hue - center + 180) % 360 - 180  # signed distance in [-180, 180]
    half_width = width / 2.0
    weight = np.clip((half_width - np.abs(diff)) / (half_width + 1e-6), 0.0, 1.0)
    # Smooth with cosine
    return 0.5 * (1.0 + np.cos(np.pi * (1.0 - weight)))


# --- Transform functions ---

def apply_white_balance(rgb: np.ndarray, params: dict) -> np.ndarray:
    """Apply white balance adjustment via Temperature and Tint.

    Uses a simplified daylight locus approximation to convert
    temperature/tint to per-channel RGB gains.
    """
    temp = float(params.get("Temperature", "5500"))
    tint = float(params.get("Tint", "0"))

    # Reference daylight at 5500K
    ref_temp = 5500.0

    # Temperature: shift blue/red balance
    # Positive temperature = warmer (more red/yellow, less blue)
    temp_ratio = temp / ref_temp
    r_gain = np.clip(0.5 + 0.5 * (temp_ratio - 1.0) * 0.8, 0.7, 1.4)
    b_gain = np.clip(0.5 + 0.5 * (1.0 / temp_ratio - 1.0) * 0.8 + 1.0, 0.7, 1.4)
    # Normalize so that mid-gray stays roughly the same
    b_gain = 1.0 / (temp_ratio ** 0.35)
    r_gain = temp_ratio ** 0.35

    # Tint: shift green/magenta balance
    tint_scale = tint / 150.0  # Normalize tint range
    g_gain = 1.0 - tint_scale * 0.15
    # Compensate R/B slightly for tint
    r_gain *= (1.0 + tint_scale * 0.05)
    b_gain *= (1.0 + tint_scale * 0.05)

    result = rgb.copy()
    result[..., 0] *= r_gain
    result[..., 1] *= g_gain
    result[..., 2] *= b_gain

    return np.clip(result, 0.0, 1.0)


def apply_saturation_vibrance(rgb: np.ndarray, params: dict) -> np.ndarray:
    """Apply global Saturation and Vibrance adjustments."""
    sat = float(params.get("Saturation", "0"))
    vib = float(params.get("Vibrance", "0"))

    if sat == 0 and vib == 0:
        return rgb

    hsl = rgb_to_hsl(rgb)
    h, s, l = hsl[..., 0], hsl[..., 1], hsl[..., 2]

    # Global saturation: linear scale
    if sat != 0:
        sat_factor = 1.0 + sat / 100.0
        s = s * sat_factor

    # Vibrance: boost low-saturation colors more, protect already-saturated colors
    if vib != 0:
        vib_factor = vib / 100.0
        # Weight inversely proportional to current saturation
        vib_weight = 1.0 - s
        s = s + vib_factor * vib_weight * 0.5

    s = np.clip(s, 0.0, 1.0)
    hsl = np.stack([h, s, l], axis=-1)
    return hsl_to_rgb(hsl)


def apply_hsl_adjustments(rgb: np.ndarray, params: dict) -> np.ndarray:
    """Apply per-channel HSL hue, saturation, and luminance adjustments."""
    color_names = ["Red", "Orange", "Yellow", "Green", "Aqua", "Blue", "Purple", "Magenta"]

    # Check if any HSL adjustments are non-zero
    has_adjustments = False
    for name in color_names:
        for prefix in ("HueAdjustment", "SaturationAdjustment", "LuminanceAdjustment"):
            if float(params.get(f"{prefix}{name}", "0")) != 0:
                has_adjustments = True
                break
        if has_adjustments:
            break

    if not has_adjustments:
        return rgb

    hsl = rgb_to_hsl(rgb)
    h, s, l = hsl[..., 0], hsl[..., 1], hsl[..., 2]

    for name in color_names:
        hue_adj = float(params.get(f"HueAdjustment{name}", "0"))
        sat_adj = float(params.get(f"SaturationAdjustment{name}", "0"))
        lum_adj = float(params.get(f"LuminanceAdjustment{name}", "0"))

        if hue_adj == 0 and sat_adj == 0 and lum_adj == 0:
            continue

        center, width = LR_HUE_RANGES[name]
        weight = _hue_weight(h, center, width)

        # Only affect pixels with meaningful saturation
        sat_mask = np.clip(s * 3.0, 0.0, 1.0)
        weight = weight * sat_mask

        # Hue rotation
        if hue_adj != 0:
            h = h + weight * hue_adj
            h = h % 360.0

        # Saturation adjustment
        if sat_adj != 0:
            sat_factor = 1.0 + (sat_adj / 100.0)
            s = s * (1.0 + weight * (sat_factor - 1.0))

        # Luminance adjustment
        if lum_adj != 0:
            lum_offset = lum_adj / 100.0
            l = l + weight * lum_offset * 0.5

    s = np.clip(s, 0.0, 1.0)
    l = np.clip(l, 0.0, 1.0)
    hsl = np.stack([h % 360.0, s, l], axis=-1)
    return hsl_to_rgb(hsl)


def _parse_tone_curve_points(curve_str) -> list[tuple[float, float]]:
    """Parse a Lightroom tone curve string into control points.

    Lightroom stores curves as "x1, y1, x2, y2, ..." strings or lists.
    """
    if isinstance(curve_str, list):
        # List of "x, y" pair strings from rdf:li elements
        # Each item is "x, y" — split each on comma
        values = []
        for item in curve_str:
            parts = [float(v.strip()) for v in item.split(",")]
            values.extend(parts)
    elif isinstance(curve_str, str):
        # "0, 0, 64, 64, 128, 128, 192, 192, 255, 255"
        values = [float(v.strip()) for v in curve_str.split(",")]
    else:
        return []

    # Pair up as (input, output) and normalize to 0-1
    points = []
    for i in range(0, len(values) - 1, 2):
        points.append((values[i] / 255.0, values[i + 1] / 255.0))

    return points


def _build_curve_lut(points: list[tuple[float, float]], size: int = 256) -> np.ndarray:
    """Build a 1D LUT from curve control points using cubic spline interpolation."""
    if not points or len(points) < 2:
        return np.linspace(0, 1, size, dtype=np.float32)

    xs = np.array([p[0] for p in points])
    ys = np.array([p[1] for p in points])

    # Ensure endpoints
    if xs[0] > 0:
        xs = np.insert(xs, 0, 0.0)
        ys = np.insert(ys, 0, 0.0)
    if xs[-1] < 1:
        xs = np.append(xs, 1.0)
        ys = np.append(ys, 1.0)

    cs = CubicSpline(xs, ys, bc_type="clamped")
    x_eval = np.linspace(0, 1, size, dtype=np.float64)
    return np.clip(cs(x_eval), 0.0, 1.0).astype(np.float32)


def apply_tone_curve(rgb: np.ndarray, params: dict) -> np.ndarray:
    """Apply parametric tone curve and point curves (RGB master + per-channel)."""
    # Parametric curve
    rgb = _apply_parametric_curve(rgb, params)
    rgb = rgb.copy()  # Ensure we don't mutate the caller's array

    # Point curves
    curve_name = params.get("ToneCurveName2012", "Linear")
    master_curve = params.get("ToneCurvePV2012")
    red_curve = params.get("ToneCurvePV2012Red")
    green_curve = params.get("ToneCurvePV2012Green")
    blue_curve = params.get("ToneCurvePV2012Blue")

    if curve_name == "Linear" and not any([master_curve, red_curve, green_curve, blue_curve]):
        return rgb

    # Master curve (applied to all channels equally)
    if master_curve:
        points = _parse_tone_curve_points(master_curve)
        if points and len(points) >= 2:
            lut = _build_curve_lut(points)
            # Apply LUT via interpolation
            rgb = _apply_1d_lut(rgb, lut)

    # Per-channel curves
    for ch_idx, curve_data in enumerate([red_curve, green_curve, blue_curve]):
        if curve_data:
            points = _parse_tone_curve_points(curve_data)
            if points and len(points) >= 2:
                lut = _build_curve_lut(points)
                rgb[..., ch_idx] = np.interp(rgb[..., ch_idx], np.linspace(0, 1, len(lut)), lut)

    return np.clip(rgb, 0.0, 1.0)


def _apply_1d_lut(rgb: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Apply a 1D LUT to all channels of an RGB array."""
    x = np.linspace(0, 1, len(lut))
    for ch in range(3):
        rgb[..., ch] = np.interp(rgb[..., ch], x, lut)
    return rgb


def _apply_parametric_curve(rgb: np.ndarray, params: dict) -> np.ndarray:
    """Apply Lightroom's parametric tone curve (zone-based)."""
    darks = float(params.get("ParametricDarks", "0"))
    lights = float(params.get("ParametricLights", "0"))
    highlights = float(params.get("ParametricHighlights", "0"))
    shadows = float(params.get("ParametricShadows", "0"))

    if darks == 0 and lights == 0 and highlights == 0 and shadows == 0:
        return rgb

    # Zone split points (configurable in Lightroom, using defaults)
    shadow_split = float(params.get("ParametricShadowSplit", "25")) / 100.0
    midtone_split = float(params.get("ParametricMidtoneSplit", "50")) / 100.0
    highlight_split = float(params.get("ParametricHighlightSplit", "75")) / 100.0

    # Build parametric curve as set of control points
    # Each zone adjusts the output at its center point
    points = [
        (0.0, 0.0),
        (shadow_split, shadow_split + (shadows / 100.0) * shadow_split),
        (midtone_split, midtone_split + (darks / 100.0) * 0.15),
        (highlight_split, highlight_split + (lights / 100.0) * 0.15),
        (1.0, 1.0 + (highlights / 100.0) * (1.0 - highlight_split)),
    ]

    # Clamp y values
    points = [(x, max(0.0, min(1.0, y))) for x, y in points]

    lut = _build_curve_lut(points)

    # Apply to luminance (approximate: apply to each channel)
    return _apply_1d_lut(rgb.copy(), lut)


def apply_color_grading(rgb: np.ndarray, params: dict) -> np.ndarray:
    """Apply Color Grading wheels (LR 10+): shadows, midtones, highlights, global."""
    zones = {
        "Shadow": {"low": 0.0, "mid": 0.15, "high": 0.35},
        "Midtone": {"low": 0.25, "mid": 0.5, "high": 0.75},
        "Highlight": {"low": 0.65, "mid": 0.85, "high": 1.0},
    }

    blending = float(params.get("ColorGradeBlending", "50")) / 100.0
    balance = float(params.get("ColorGradeBalance", "0"))

    has_grading = False
    for zone in ["Shadow", "Midtone", "Highlight", "Global"]:
        h = float(params.get(f"ColorGrade{zone}Hue", "0"))
        s = float(params.get(f"ColorGrade{zone}Sat", "0"))
        lum = float(params.get(f"ColorGrade{zone}Lum", "0"))
        if h != 0 or s != 0 or lum != 0:
            has_grading = True
            break

    if not has_grading:
        return rgb

    result = rgb.copy()
    hsl = rgb_to_hsl(result)
    luminance = hsl[..., 2]

    for zone_name, zone_range in zones.items():
        grade_hue = float(params.get(f"ColorGrade{zone_name}Hue", "0"))
        grade_sat = float(params.get(f"ColorGrade{zone_name}Sat", "0"))
        grade_lum = float(params.get(f"ColorGrade{zone_name}Lum", "0"))

        if grade_hue == 0 and grade_sat == 0 and grade_lum == 0:
            continue

        # Compute zone mask with smooth falloff
        low, mid, high = zone_range["low"], zone_range["mid"], zone_range["high"]
        mask = np.zeros_like(luminance)

        # Rising edge
        rising = (luminance >= low) & (luminance < mid)
        if np.any(rising):
            mask[rising] = (luminance[rising] - low) / (mid - low + 1e-10)

        # Falling edge
        falling = (luminance >= mid) & (luminance <= high)
        if np.any(falling):
            mask[falling] = (high - luminance[falling]) / (high - mid + 1e-10)

        # Smooth the mask
        mask = mask ** (1.0 + blending)

        # Apply hue/sat tint
        if grade_sat > 0:
            tint_hue_rad = np.radians(grade_hue)
            intensity = (grade_sat / 100.0) * mask * 0.3
            result[..., 0] += np.cos(tint_hue_rad) * intensity
            result[..., 1] += np.cos(tint_hue_rad - 2.094) * intensity  # -120 deg
            result[..., 2] += np.cos(tint_hue_rad + 2.094) * intensity  # +120 deg

        # Apply luminance offset
        if grade_lum != 0:
            lum_offset = (grade_lum / 100.0) * mask * 0.3
            result += lum_offset[..., np.newaxis]

    # Global grading
    global_hue = float(params.get("ColorGradeGlobalHue", "0"))
    global_sat = float(params.get("ColorGradeGlobalSat", "0"))
    global_lum = float(params.get("ColorGradeGlobalLum", "0"))

    if global_sat > 0:
        tint_hue_rad = np.radians(global_hue)
        intensity = global_sat / 100.0 * 0.15
        result[..., 0] += np.cos(tint_hue_rad) * intensity
        result[..., 1] += np.cos(tint_hue_rad - 2.094) * intensity
        result[..., 2] += np.cos(tint_hue_rad + 2.094) * intensity

    if global_lum != 0:
        result += (global_lum / 100.0) * 0.15

    return np.clip(result, 0.0, 1.0)


def apply_split_toning(rgb: np.ndarray, params: dict) -> np.ndarray:
    """Apply legacy Split Toning (pre-LR 10)."""
    sh_hue = float(params.get("SplitToningShadowHue", "0"))
    sh_sat = float(params.get("SplitToningShadowSaturation", "0"))
    hl_hue = float(params.get("SplitToningHighlightHue", "0"))
    hl_sat = float(params.get("SplitToningHighlightSaturation", "0"))
    balance = float(params.get("SplitToningBalance", "0"))

    if sh_sat == 0 and hl_sat == 0:
        return rgb

    result = rgb.copy()
    hsl = rgb_to_hsl(result)
    luminance = hsl[..., 2]

    # Balance shifts the midpoint: negative = more shadow toning, positive = more highlight
    mid = 0.5 + (balance / 100.0) * 0.25

    # Shadow toning
    if sh_sat > 0:
        shadow_mask = np.clip((mid - luminance) / (mid + 1e-10), 0.0, 1.0)
        sh_hue_rad = np.radians(sh_hue)
        intensity = (sh_sat / 100.0) * shadow_mask * 0.25
        result[..., 0] += np.cos(sh_hue_rad) * intensity
        result[..., 1] += np.cos(sh_hue_rad - 2.094) * intensity
        result[..., 2] += np.cos(sh_hue_rad + 2.094) * intensity

    # Highlight toning
    if hl_sat > 0:
        highlight_mask = np.clip((luminance - mid) / (1.0 - mid + 1e-10), 0.0, 1.0)
        hl_hue_rad = np.radians(hl_hue)
        intensity = (hl_sat / 100.0) * highlight_mask * 0.25
        result[..., 0] += np.cos(hl_hue_rad) * intensity
        result[..., 1] += np.cos(hl_hue_rad - 2.094) * intensity
        result[..., 2] += np.cos(hl_hue_rad + 2.094) * intensity

    return np.clip(result, 0.0, 1.0)


def apply_color_pipeline(rgb: np.ndarray, params: dict) -> np.ndarray:
    """Apply the full Lightroom color transform pipeline in correct order.

    Args:
        rgb: float32 array of shape (N, 3), values 0.0–1.0 (Hald identity).
        params: Sanitized XMP parameters dict.

    Returns:
        Transformed float32 array of same shape.
    """
    result = rgb.copy()

    # 1. White Balance
    result = apply_white_balance(result, params)

    # 2. Global Saturation / Vibrance
    result = apply_saturation_vibrance(result, params)

    # 3. HSL adjustments
    result = apply_hsl_adjustments(result, params)

    # 4. Tone Curve
    result = apply_tone_curve(result, params)

    # 5. Color Grading wheels
    result = apply_color_grading(result, params)

    # 6. Split Toning (legacy)
    result = apply_split_toning(result, params)

    return np.clip(result, 0.0, 1.0).astype(np.float32)
