"""Auto-detect default paths for Lightroom presets and DaVinci Resolve LUTs."""

import glob
import os
import platform


def detect_paths() -> dict[str, str]:
    """Detect default Lightroom presets and DaVinci LUT directories.

    Returns a dict with keys 'lightroom' and 'davinci', each containing
    the detected path or an empty string if not found.

    For Lightroom: prefers the first candidate that contains .xmp files over
    one that merely exists but is empty — so a populated factory-presets folder
    beats an empty user folder.
    """
    system = platform.system()

    if system == "Darwin":
        candidates = _detect_mac_paths()
    elif system == "Windows":
        candidates = _detect_windows_paths()
    else:
        candidates = _detect_linux_paths()

    result = {}
    for key, paths in candidates.items():
        result[key] = _pick_best(paths, require_xmp=(key == "lightroom"))

    # DaVinci: if nothing existed OR we fell back to the bare LUT root, prefer
    # the dedicated LR-Presets subfolder so we never mix with stock LUTs.
    dv = result.get("davinci", "")
    if dv and os.path.basename(dv) != "LR-Presets":
        candidate = os.path.join(dv, "LR-Presets")
        if os.path.isdir(os.path.dirname(candidate)):
            result["davinci"] = candidate
    return result


def _pick_best(paths: list[str], require_xmp: bool) -> str:
    """Return the best-matching path from candidates.

    If require_xmp is True, prefer the first candidate that actually contains
    .xmp files (recursively). Fall back to the first existing directory.
    """
    first_existing = ""
    for path in paths:
        if not os.path.isdir(path):
            continue
        if not first_existing:
            first_existing = path
        if not require_xmp:
            return path
        if _contains_xmp(path):
            return path
    return first_existing


def _contains_xmp(root: str, limit: int = 1) -> bool:
    """True if root contains at least `limit` .xmp files anywhere below it."""
    found = 0
    for _dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.lower().endswith(".xmp"):
                found += 1
                if found >= limit:
                    return True
    return False


def _detect_mac_paths() -> dict[str, list[str]]:
    home = os.path.expanduser("~")
    lr_candidates: list[str] = [
        # User-level Camera Raw Settings — modern LrC stores user-created
        # presets here (Adaptive, Portraits, Seasons, Style, Subject groups).
        os.path.join(home, "Library", "Application Support", "Adobe",
                     "CameraRaw", "Settings"),
        # System-wide Camera Raw Settings — shared with Photoshop, contains
        # the bundled Premium and Adobe Presets (Color, Creative, B&W, etc.).
        "/Library/Application Support/Adobe/CameraRaw/Settings",
        # Legacy LrC user Develop Presets (older layout)
        os.path.join(home, "Library", "Application Support", "Adobe",
                     "Lightroom", "Develop Presets"),
    ]
    # Factory presets inside the Lightroom Classic app bundle (read-only
    # fallback when nothing else has .xmp files).
    for bundle in sorted(
        glob.glob("/Applications/Adobe Lightroom Classic*/Adobe Lightroom Classic*.app")
        + glob.glob("/Applications/Adobe Lightroom Classic.app"),
        reverse=True,
    ):
        lr_candidates.append(os.path.join(bundle, "Contents", "Resources", "Settings"))

    return {
        "lightroom": lr_candidates,
        "davinci": [
            # Put LUTs in a dedicated subfolder so we never mix with stock LUTs
            "/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/LR-Presets",
            "/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT",
            os.path.join(home, "Library", "Application Support",
                         "Blackmagic Design", "DaVinci Resolve", "LUT"),
        ],
    }


def _detect_windows_paths() -> dict[str, list[str]]:
    appdata = os.environ.get("APPDATA", "")
    programdata = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
    programfiles = os.environ.get("PROGRAMFILES", "C:\\Program Files")
    lr_candidates: list[str] = [
        os.path.join(appdata, "Adobe", "Lightroom", "Develop Presets"),
        os.path.join(appdata, "Adobe", "CameraRaw", "Settings"),
    ]
    # Factory presets inside the LrC install directory
    for install in sorted(
        glob.glob(os.path.join(programfiles, "Adobe", "Adobe Lightroom Classic*")),
        reverse=True,
    ):
        lr_candidates.append(os.path.join(install, "Resources", "en-US", "Settings"))
        lr_candidates.append(os.path.join(install, "Resources", "Settings"))

    return {
        "lightroom": lr_candidates,
        "davinci": [
            os.path.join(programdata, "Blackmagic Design",
                         "DaVinci Resolve", "Support", "LUT"),
        ],
    }


def _detect_linux_paths() -> dict[str, list[str]]:
    home = os.path.expanduser("~")
    return {
        "lightroom": [
            os.path.join(home, ".wine", "drive_c", "users", os.getlogin(),
                         "AppData", "Roaming", "Adobe", "Lightroom",
                         "Develop Presets"),
        ],
        "davinci": [
            os.path.join(home, ".local", "share", "DaVinciResolve", "LUT"),
            "/opt/resolve/LUT",
        ],
    }
