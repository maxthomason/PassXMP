"""XMP parsing and sanitization for Lightroom preset files."""

import xml.etree.ElementTree as ET

CRS_NS = "http://ns.adobe.com/camera-raw-settings/1.0/"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

# Parameters that can be accurately encoded in a 3D LUT.
COLOR_SAFE_PARAMS = {
    # White Balance
    "Temperature", "Tint",
    # Vibrance / Saturation
    "Vibrance", "Saturation",
    # Parametric Tone Curve
    "ParametricDarks", "ParametricLights",
    "ParametricHighlights", "ParametricShadows",
    "ParametricHighlightSplit", "ParametricMidtoneSplit", "ParametricShadowSplit",
    # HSL Hue
    "HueAdjustmentRed", "HueAdjustmentOrange", "HueAdjustmentYellow",
    "HueAdjustmentGreen", "HueAdjustmentAqua", "HueAdjustmentBlue",
    "HueAdjustmentPurple", "HueAdjustmentMagenta",
    # HSL Saturation
    "SaturationAdjustmentRed", "SaturationAdjustmentOrange", "SaturationAdjustmentYellow",
    "SaturationAdjustmentGreen", "SaturationAdjustmentAqua", "SaturationAdjustmentBlue",
    "SaturationAdjustmentPurple", "SaturationAdjustmentMagenta",
    # HSL Luminance
    "LuminanceAdjustmentRed", "LuminanceAdjustmentOrange", "LuminanceAdjustmentYellow",
    "LuminanceAdjustmentGreen", "LuminanceAdjustmentAqua", "LuminanceAdjustmentBlue",
    "LuminanceAdjustmentPurple", "LuminanceAdjustmentMagenta",
    # Split Toning (legacy)
    "SplitToningHighlightHue", "SplitToningHighlightSaturation",
    "SplitToningShadowHue", "SplitToningShadowSaturation", "SplitToningBalance",
    # Color Grading (LR 10+)
    "ColorGradeHighlightHue", "ColorGradeHighlightSat", "ColorGradeHighlightLum",
    "ColorGradeMidtoneHue", "ColorGradeMidtoneSat", "ColorGradeMidtoneLum",
    "ColorGradeShadowHue", "ColorGradeShadowSat", "ColorGradeShadowLum",
    "ColorGradeGlobalHue", "ColorGradeGlobalSat", "ColorGradeGlobalLum",
    "ColorGradeBlending", "ColorGradeBalance",
    # Tone Curves (point curves)
    "ToneCurvePV2012", "ToneCurvePV2012Red",
    "ToneCurvePV2012Green", "ToneCurvePV2012Blue",
    "ToneCurveName2012",
}

# Parameters that are explicitly zeroed out because they cannot be
# represented in a 3D LUT.
ZEROED_PARAMS = {
    "Exposure2012", "Contrast2012", "Highlights2012", "Shadows2012",
    "Whites2012", "Blacks2012",
    "Clarity2012", "Texture", "Dehaze",
    "Sharpness", "SharpenRadius", "SharpenDetail", "SharpenEdgeMasking",
    "LuminanceSmoothing", "LuminanceNoiseReductionDetail",
    "LuminanceNoiseReductionContrast",
    "ColorNoiseReduction", "ColorNoiseReductionDetail",
    "ColorNoiseReductionSmoothness",
    "VignetteAmount", "PostCropVignetteAmount",
    "LensProfileEnable", "LensManualDistortionAmount",
    "AutoLateralCA", "ChromaticAberrationB", "ChromaticAberrationR",
    "UprightVersion", "UprightTransform_0", "UprightTransform_1",
    "UprightTransform_2", "UprightTransform_3", "UprightTransform_4",
    "UprightTransform_5",
    "PerspectiveUpright",
    "GrainAmount",
}


def parse_xmp(filepath: str) -> dict:
    """Parse a Lightroom .xmp file and return all crs: parameters as a dict."""
    tree = ET.parse(filepath)
    root = tree.getroot()

    params = {}

    # Walk all elements looking for crs: namespace attributes
    for elem in root.iter():
        for attr_name, attr_val in elem.attrib.items():
            if CRS_NS in attr_name:
                key = attr_name.split("}")[-1]
                params[key] = attr_val

    # Also check for child elements with crs: namespace (tone curves stored as child elements)
    for elem in root.iter():
        tag = elem.tag
        if tag.startswith(f"{{{CRS_NS}"):
            key = tag.split("}")[-1]
            # If the element has child <rdf:Seq>/<rdf:li> structure, collect list values
            seq = elem.find(f".//{{{RDF_NS}}}Seq")
            if seq is not None:
                items = [li.text for li in seq.findall(f"{{{RDF_NS}}}li") if li.text]
                params[key] = items
            elif elem.text and elem.text.strip():
                params[key] = elem.text.strip()

    return params


def sanitize(params: dict) -> dict:
    """Zero out non-color parameters, preserving only color-safe values.

    Parameters in COLOR_SAFE_PARAMS are kept as-is.
    Parameters in ZEROED_PARAMS are set to "0".
    Unknown parameters are left as-is (future-proof for new color params).
    Tone curve values (list type) are kept for COLOR_SAFE_PARAMS, dropped otherwise.
    """
    result = {}
    for key, value in params.items():
        if key in COLOR_SAFE_PARAMS:
            result[key] = value
        elif key in ZEROED_PARAMS:
            if isinstance(value, list):
                result[key] = []
            else:
                result[key] = "0"
        else:
            # Keep unknown params — they may be metadata or new color params
            result[key] = value
    return result
