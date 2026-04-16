"""Canonical per-.xmp file state and the registry that owns it."""

from dataclasses import dataclass, field
from typing import Literal

Status = Literal["synced", "pending", "syncing", "failed"]


@dataclass
class FileState:
    xmp_path: str
    cube_path: str
    folder: str
    xmp_mtime: float
    cube_mtime: float | None = None
    selected: bool = False
    last_error: str | None = None


def derive_status(
    state: FileState,
    in_flight: set[str],
    failed: set[str],
) -> Status:
    """Compute the visible status from raw state + in-flight/failed sets.

    Order matters: syncing > failed > synced > pending.
    """
    if state.xmp_path in in_flight:
        return "syncing"
    if state.xmp_path in failed:
        return "failed"
    if state.cube_mtime is not None and state.cube_mtime >= state.xmp_mtime:
        return "synced"
    return "pending"
