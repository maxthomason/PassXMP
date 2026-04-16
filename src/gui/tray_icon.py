"""System tray / menu bar icon for PassXMP."""

import os

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore import pyqtSignal, QObject


class TrayIcon(QObject):
    """System tray icon with context menu."""

    show_requested = pyqtSignal()
    sync_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tray = QSystemTrayIcon(parent)
        self._tray.activated.connect(self._on_activated)

        # Create a simple colored dot icon as fallback
        self._green_icon = self._make_dot_icon("#22c55e")
        self._yellow_icon = self._make_dot_icon("#eab308")

        self._tray.setIcon(self._green_icon)
        self._tray.setToolTip("PassXMP — Syncing")

        # Context menu
        menu = QMenu()
        self._show_action = menu.addAction("Show PassXMP")
        self._show_action.triggered.connect(self.show_requested.emit)

        menu.addSeparator()

        self._pause_action = menu.addAction("Pause")
        self._pause_action.triggered.connect(self.pause_requested.emit)

        self._sync_action = menu.addAction("Sync Now")
        self._sync_action.triggered.connect(self.sync_requested.emit)

        menu.addSeparator()

        self._quit_action = menu.addAction("Quit PassXMP")
        self._quit_action.triggered.connect(self.quit_requested.emit)

        self._tray.setContextMenu(menu)

    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    def set_syncing(self, active: bool) -> None:
        if active:
            self._tray.setIcon(self._green_icon)
            self._tray.setToolTip("PassXMP — Syncing")
            self._pause_action.setText("Pause")
        else:
            self._tray.setIcon(self._yellow_icon)
            self._tray.setToolTip("PassXMP — Paused")
            self._pause_action.setText("Resume")

    def show_message(self, title: str, message: str) -> None:
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_requested.emit()

    @staticmethod
    def _make_dot_icon(color: str) -> QIcon:
        """Create a simple colored circle icon."""
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(QColor(color))
        painter.drawEllipse(8, 8, size - 16, size - 16)
        painter.end()
        return QIcon(pixmap)
