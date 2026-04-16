"""Main window showing sync status and recent activity."""

import time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt6.QtGui import QFont


class ActivityItem(QWidget):
    """Single activity log entry widget."""

    def __init__(self, xmp_rel: str, cube_rel: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        check = QLabel("\u2713")
        check.setStyleSheet("color: #22c55e; font-weight: bold;")
        check.setFixedWidth(16)
        layout.addWidget(check)

        text = QLabel(f"{xmp_rel} \u2192 {cube_rel}")
        text.setStyleSheet("color: #444; font-size: 12px;")
        text.setWordWrap(True)
        layout.addWidget(text, 1)


class MainWindow(QWidget):
    """Active sync status screen — the primary window after setup."""

    sync_all_requested = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PassXMP")
        self.setMinimumSize(480, 400)
        self._synced_count = 0
        self._last_sync_name = ""
        self._last_sync_time = 0.0
        self._init_ui()

        # Timer to update "X min ago" display
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_time_display)
        self._timer.start(30_000)  # every 30s

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        # Header
        header = QHBoxLayout()
        title = QLabel("PassXMP")
        title.setFont(QFont("", 18, QFont.Weight.Bold))
        header.addWidget(title)

        self._status_dot = QLabel("\u25cf")
        self._status_dot.setStyleSheet("color: #22c55e; font-size: 16px;")
        header.addWidget(self._status_dot)

        self._status_label = QLabel("Syncing")
        self._status_label.setStyleSheet("color: #22c55e; font-weight: bold;")
        header.addWidget(self._status_label)
        header.addStretch()
        layout.addLayout(header)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #e5e7eb;")
        layout.addWidget(line)

        # Stats
        self._count_label = QLabel("0 presets synced")
        self._count_label.setFont(QFont("", 14))
        layout.addWidget(self._count_label)

        self._last_label = QLabel("")
        self._last_label.setStyleSheet("color: #888;")
        layout.addWidget(self._last_label)

        # Separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("color: #e5e7eb;")
        layout.addWidget(line2)

        # Activity label
        activity_title = QLabel("Recent Activity")
        activity_title.setFont(QFont("", 12, QFont.Weight.DemiBold))
        layout.addWidget(activity_title)

        # Scrollable activity list
        self._activity_area = QScrollArea()
        self._activity_area.setWidgetResizable(True)
        self._activity_area.setFrameShape(QFrame.Shape.NoFrame)
        self._activity_widget = QWidget()
        self._activity_layout = QVBoxLayout(self._activity_widget)
        self._activity_layout.setSpacing(2)
        self._activity_layout.setContentsMargins(0, 0, 0, 0)
        self._activity_layout.addStretch()
        self._activity_area.setWidget(self._activity_widget)
        layout.addWidget(self._activity_area, 1)

        # Bottom buttons
        btn_row = QHBoxLayout()
        self._sync_btn = QPushButton("Sync All Now")
        self._sync_btn.setFixedHeight(36)
        self._sync_btn.clicked.connect(self.sync_all_requested.emit)
        btn_row.addWidget(self._sync_btn)

        self._settings_btn = QPushButton("Settings")
        self._settings_btn.setFixedHeight(36)
        self._settings_btn.clicked.connect(self.settings_requested.emit)
        btn_row.addWidget(self._settings_btn)
        layout.addLayout(btn_row)

    @pyqtSlot(str, str)
    def add_activity(self, xmp_rel: str, cube_rel: str) -> None:
        """Add a sync activity entry to the log."""
        self._synced_count += 1
        self._last_sync_name = xmp_rel.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        self._last_sync_time = time.time()

        self._count_label.setText(f"{self._synced_count} presets synced")
        self._update_time_display()

        item = ActivityItem(xmp_rel, cube_rel)
        # Insert before the stretch
        count = self._activity_layout.count()
        self._activity_layout.insertWidget(max(0, count - 1), item)

        # Keep only last 100 entries
        while self._activity_layout.count() > 101:  # 100 items + 1 stretch
            w = self._activity_layout.takeAt(0)
            if w.widget():
                w.widget().deleteLater()

        # Scroll to bottom
        QTimer.singleShot(50, lambda: self._activity_area.verticalScrollBar().setValue(
            self._activity_area.verticalScrollBar().maximum()
        ))

    def set_synced_count(self, count: int) -> None:
        self._synced_count = count
        self._count_label.setText(f"{self._synced_count} presets synced")

    def set_status(self, running: bool) -> None:
        if running:
            self._status_dot.setStyleSheet("color: #22c55e; font-size: 16px;")
            self._status_label.setText("Syncing")
            self._status_label.setStyleSheet("color: #22c55e; font-weight: bold;")
        else:
            self._status_dot.setStyleSheet("color: #eab308; font-size: 16px;")
            self._status_label.setText("Paused")
            self._status_label.setStyleSheet("color: #eab308; font-weight: bold;")

    def _update_time_display(self) -> None:
        if self._last_sync_time == 0:
            self._last_label.setText("")
            return

        elapsed = time.time() - self._last_sync_time
        if elapsed < 60:
            ago = "just now"
        elif elapsed < 3600:
            mins = int(elapsed / 60)
            ago = f"{mins} min ago"
        else:
            hours = int(elapsed / 3600)
            ago = f"{hours} hr ago"

        self._last_label.setText(f"Last sync: {self._last_sync_name} \u2014 {ago}")
