"""Tiny helpers — deliberately minimal so Qt renders natively."""

from PyQt6.QtWidgets import QLabel


def make_muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("color: palette(placeholder-text);")
    return label
