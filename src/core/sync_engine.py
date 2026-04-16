"""Orchestrates the full XMP-to-CUBE conversion pipeline for a single file."""

import logging
import os

from .xmp_parser import parse_xmp, sanitize
from .hald_generator import generate_hald_identity
from .color_transforms import apply_color_pipeline
from .cube_exporter import write_cube

logger = logging.getLogger("passxmp.sync_engine")


def process_xmp_file(
    xmp_path: str,
    cube_path: str,
    lut_size: int = 33,
) -> bool:
    """Convert a single .xmp preset file to a .cube LUT file.

    Args:
        xmp_path: Path to the Lightroom .xmp preset file.
        cube_path: Output path for the .cube LUT file.
        lut_size: LUT resolution (33 or 65).

    Returns:
        True if conversion succeeded, False otherwise.
    """
    try:
        # 1. Parse XMP
        logger.info("Parsing XMP: %s", xmp_path)
        params = parse_xmp(xmp_path)

        if not params:
            logger.warning("No CRS parameters found in %s", xmp_path)
            return False

        # 2. Sanitize — zero out non-color parameters
        clean_params = sanitize(params)

        # 3. Generate Hald identity
        identity = generate_hald_identity(size=lut_size)

        # 4. Apply color pipeline
        logger.info("Applying color transforms...")
        transformed = apply_color_pipeline(identity, clean_params)

        # 5. Write .cube file
        os.makedirs(os.path.dirname(cube_path), exist_ok=True)
        title = os.path.splitext(os.path.basename(cube_path))[0]
        write_cube(transformed, cube_path, title=title, size=lut_size)

        logger.info("Written CUBE: %s", cube_path)
        return True

    except ET.ParseError:
        logger.error("Failed to parse XML in %s", xmp_path)
        return False
    except Exception:
        logger.exception("Error processing %s", xmp_path)
        return False


# Import ET for exception handling
import xml.etree.ElementTree as ET
