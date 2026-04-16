"""Auto-detect default paths for Lightroom presets and DaVinci Resolve LUTs."""

import os
import platform


def detect_paths() -> dict[str, str]:
    """Detect default Lightroom presets and DaVinci LUT directories.

    Returns a dict with keys 'lightroom' and 'davinci', each containing
    the detected path or an empty string if not found.
    """
    system = platform.system()

    if system == "Darwin":
        candidates = _detect_mac_paths()
    elif system == "Windows":
        candidates = _detect_windows_paths()
    else:
        candidates = _detect_linux_paths()

    # Verify paths exist
    result = {}
    for key, paths in candidates.items():
        result[key] = ""
        for path in paths:
            if os.path.isdir(path):
                result[key] = path
                break

    return result


def _detect_mac_paths() -> dict[str, list[str]]:
    home = os.path.expanduser("~")
    return {
        "lightroom": [
            # Lightroom Classic CC (current)
            os.path.join(home, "Library", "Application Support", "Adobe",
                         "Lightroom", "Develop Presets"),
            # Lightroom Classic (alternate location)
            os.path.join(home, "Library", "Application Support", "Adobe",
                         "CameraRaw", "Settings"),
        ],
        "davinci": [
            # DaVinci Resolve system LUT folder
            "/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT",
            # User-level LUT folder
            os.path.join(home, "Library", "Application Support",
                         "Blackmagic Design", "DaVinci Resolve", "LUT"),
        ],
    }


def _detect_windows_paths() -> dict[str, list[str]]:
    appdata = os.environ.get("APPDATA", "")
    programdata = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
    return {
        "lightroom": [
            os.path.join(appdata, "Adobe", "Lightroom", "Develop Presets"),
            os.path.join(appdata, "Adobe", "CameraRaw", "Settings"),
        ],
        "davinci": [
            os.path.join(programdata, "Blackmagic Design",
                         "DaVinci Resolve", "Support", "LUT"),
        ],
    }


def _detect_linux_paths() -> dict[str, list[str]]:
    home = os.path.expanduser("~")
    return {
        "lightroom": [
            # Wine/Proton paths (unlikely but possible)
            os.path.join(home, ".wine", "drive_c", "users", os.getlogin(),
                         "AppData", "Roaming", "Adobe", "Lightroom",
                         "Develop Presets"),
        ],
        "davinci": [
            os.path.join(home, ".local", "share", "DaVinciResolve", "LUT"),
            "/opt/resolve/LUT",
        ],
    }
