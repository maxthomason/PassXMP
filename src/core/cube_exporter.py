"""Export 3D LUT data to the .cube file format."""

import os

import numpy as np


def write_cube(lut_data: np.ndarray, filepath: str, title: str, size: int = 33) -> None:
    """Write LUT data to a .cube file.

    Args:
        lut_data: float32 array of shape (size**3, 3), values 0.0–1.0.
        filepath: Output path for the .cube file.
        title: Title string embedded in the .cube header.
        size: LUT resolution (must match lut_data dimensions).

    The write is atomic: output goes to a ``.tmp`` sibling and is renamed
    into place only after the body is fully written. A crash mid-write
    leaves no half-finished ``.cube`` whose newer mtime would fool the
    freshness check into skipping re-conversion.
    """
    expected_count = size ** 3
    if lut_data.shape != (expected_count, 3):
        raise ValueError(
            f"Expected LUT data shape ({expected_count}, 3), got {lut_data.shape}"
        )

    lut_data = np.clip(lut_data, 0.0, 1.0)
    safe_title = "".join(c for c in title if c.isprintable() and c not in '"\n\r')

    tmp_path = filepath + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            f.write(f'TITLE "{safe_title}"\n')
            f.write(f"LUT_3D_SIZE {size}\n")
            f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
            f.write("DOMAIN_MAX 1.0 1.0 1.0\n")
            f.write("\n")
            for r, g, b in lut_data:
                f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")
        os.replace(tmp_path, filepath)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise
