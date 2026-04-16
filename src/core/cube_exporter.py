"""Export 3D LUT data to the .cube file format."""

import numpy as np


def write_cube(lut_data: np.ndarray, filepath: str, title: str, size: int = 33) -> None:
    """Write LUT data to a .cube file.

    Args:
        lut_data: float32 array of shape (size**3, 3), values 0.0–1.0.
        filepath: Output path for the .cube file.
        title: Title string embedded in the .cube header.
        size: LUT resolution (must match lut_data dimensions).
    """
    expected_count = size ** 3
    if lut_data.shape != (expected_count, 3):
        raise ValueError(
            f"Expected LUT data shape ({expected_count}, 3), got {lut_data.shape}"
        )

    # Clamp values to valid range
    lut_data = np.clip(lut_data, 0.0, 1.0)

    with open(filepath, "w") as f:
        f.write(f'TITLE "{title}"\n')
        f.write(f"LUT_3D_SIZE {size}\n")
        f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write("DOMAIN_MAX 1.0 1.0 1.0\n")
        f.write("\n")
        for r, g, b in lut_data:
            f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")
