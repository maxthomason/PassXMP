"""Status-column rendering for the presets table.

Synced  -> green ✓
Failed  -> red !
Pending -> blank
Syncing -> blank (the "syncing…" label is drawn inline with the filename).
"""

from typing import Literal
from PyQt6.QtGui import QColor


Status = Literal["synced", "pending", "syncing", "failed"]

STATUS_COLORS = {
    "ok": QColor(50, 180, 80),       # was (58, 143, 58) — brighter, still green
    "fail": QColor(236, 95, 88),     # was (199, 53, 42) — brighter red
    "muted": QColor(142, 142, 147),  # unchanged
}


def status_display(status: Status) -> tuple[str, str]:
    """Return (glyph, color_role) for the given status.

    color_role is one of the keys in STATUS_COLORS.
    """
    if status == "synced":
        return ("✓", "ok")
    if status == "failed":
        return ("!", "fail")
    return ("", "muted")
