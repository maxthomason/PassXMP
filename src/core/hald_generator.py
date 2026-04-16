"""Hald CLUT identity image generator."""

import numpy as np


def generate_hald_identity(size: int = 33) -> np.ndarray:
    """Generate a Hald CLUT identity array.

    Returns a float32 array of shape (size**3, 3) representing every possible
    RGB combination at the given resolution. Values range from 0.0 to 1.0.

    For a size of 33, this produces 35,937 color samples — sufficient for
    high-quality 3D LUT generation.
    """
    steps = np.linspace(0.0, 1.0, size, dtype=np.float32)
    # Meshgrid ordering: B varies fastest, then G, then R
    # This matches the standard .cube file ordering
    bb, gg, rr = np.meshgrid(steps, steps, steps, indexing="ij")
    identity = np.stack([rr.ravel(), gg.ravel(), bb.ravel()], axis=-1)
    return identity
