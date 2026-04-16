"""Path mirroring and folder sync logic.

Preserves the full folder hierarchy when mirroring .xmp files from
the Lightroom presets folder to the DaVinci LUT folder.
"""

import logging
import os

from ..core.sync_engine import process_xmp_file

logger = logging.getLogger("passxmp.mirror")


def get_mirror_path(xmp_path: str, lr_root: str, dv_root: str) -> str:
    """Compute the .cube output path that mirrors the .xmp source path.

    Preserves folder hierarchy: if the XMP is at
      lr_root/VSCO/A4.xmp
    the cube will be at
      dv_root/VSCO/A4.cube
    """
    relative = os.path.relpath(xmp_path, lr_root)
    cube_relative = os.path.splitext(relative)[0] + ".cube"
    return os.path.join(dv_root, cube_relative)


def delete_cube_mirror(xmp_path: str, lr_root: str, dv_root: str) -> bool:
    """Delete the .cube file that mirrors a deleted .xmp file."""
    cube_path = get_mirror_path(xmp_path, lr_root, dv_root)
    if os.path.exists(cube_path):
        try:
            os.remove(cube_path)
            logger.info("Deleted CUBE: %s", cube_path)
            # Clean up empty parent directories
            _cleanup_empty_dirs(os.path.dirname(cube_path), dv_root)
            return True
        except OSError:
            logger.exception("Failed to delete %s", cube_path)
            return False
    return False


def move_cube_mirror(
    old_xmp_path: str,
    new_xmp_path: str,
    lr_root: str,
    dv_root: str,
) -> bool:
    """Move/rename the .cube file to match a moved/renamed .xmp file."""
    old_cube = get_mirror_path(old_xmp_path, lr_root, dv_root)
    new_cube = get_mirror_path(new_xmp_path, lr_root, dv_root)

    if os.path.exists(old_cube):
        try:
            os.makedirs(os.path.dirname(new_cube), exist_ok=True)
            os.rename(old_cube, new_cube)
            logger.info("Moved CUBE: %s -> %s", old_cube, new_cube)
            _cleanup_empty_dirs(os.path.dirname(old_cube), dv_root)
            return True
        except OSError:
            logger.exception("Failed to move %s -> %s", old_cube, new_cube)
            return False
    return False


def initial_sync(
    lr_root: str,
    dv_root: str,
    lut_size: int = 33,
    on_progress: callable = None,
    on_scan: callable = None,
    is_cancelled: callable = None,
) -> tuple[int, int]:
    """Walk the Lightroom presets folder and convert all .xmp files.

    Symlinks inside ``lr_root`` are NOT followed — the os.walk default. A
    hostile symlink can't redirect the walk to ``/etc`` or a network share.

    Only converts files that don't already have a corresponding .cube file,
    or where the .xmp is newer than the existing .cube.

    Args:
        lr_root: Lightroom presets root directory.
        dv_root: DaVinci LUT root directory.
        lut_size: LUT resolution.
        on_progress: Callback(current, total, xmp_path) called after each file.
        on_scan: Callback(dirpath, found_so_far) called while walking the tree.

    Returns:
        Tuple of (converted_count, total_xmp_count).
    """
    xmp_files = []
    for dirpath, _, filenames in os.walk(lr_root):
        if is_cancelled and is_cancelled():
            return 0, 0
        if on_scan:
            on_scan(dirpath, len(xmp_files))
        for filename in filenames:
            if filename.lower().endswith(".xmp"):
                xmp_files.append(os.path.join(dirpath, filename))

    total = len(xmp_files)
    converted = 0

    for i, xmp_path in enumerate(xmp_files):
        if is_cancelled and is_cancelled():
            break
        cube_path = get_mirror_path(xmp_path, lr_root, dv_root)

        if os.path.exists(cube_path):
            xmp_mtime = os.path.getmtime(xmp_path)
            cube_mtime = os.path.getmtime(cube_path)
            if cube_mtime >= xmp_mtime:
                if on_progress:
                    on_progress(i + 1, total, xmp_path)
                continue

        success = process_xmp_file(xmp_path, cube_path, lut_size)
        if success:
            converted += 1

        if on_progress:
            on_progress(i + 1, total, xmp_path)

    logger.info("Initial sync complete: %d/%d converted", converted, total)
    return converted, total


def _cleanup_empty_dirs(dirpath: str, root: str) -> None:
    """Remove empty directories up to (but not including) root.

    Both paths are normalised so a trailing slash on ``root`` (from a hand-typed
    config value, for example) cannot make the loop "miss" the root and delete
    the user's DaVinci LUT folder itself.
    """
    root = os.path.normpath(root)
    dirpath = os.path.normpath(dirpath)
    while dirpath != root and dirpath != os.path.dirname(dirpath):
        try:
            if os.path.isdir(dirpath) and not os.listdir(dirpath):
                os.rmdir(dirpath)
                logger.debug("Removed empty dir: %s", dirpath)
                dirpath = os.path.dirname(dirpath)
            else:
                break
        except OSError:
            break
