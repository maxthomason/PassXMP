"""Top-level window: segmented control that switches between Presets and Settings."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QPushButton,
    QButtonGroup, QLabel,
)

from ..core.file_registry import FileRegistry
from .presets_view import PresetsView
from .settings_view import SettingsView


_SEG_STYLE = """
QWidget#SegContainer { background: palette(button); border-radius: 6px; padding: 2px; }
QPushButton { background: transparent; color: palette(text); border: none;
              padding: 4px 14px; font-size: 12px; }
QPushButton:checked { background: palette(base);
                      color: palette(highlighted-text); }
"""


class MainWindow(QWidget):
    config_changed = pyqtSignal(str, str, int, bool)
    sync_requested = pyqtSignal(list)     # list[FileState]
    stop_requested = pyqtSignal()
    pause_toggled = pyqtSignal(bool)      # True = now paused

    def __init__(
        self,
        registry: FileRegistry,
        lr_path: str, dv_path: str,
        lut_size: int, auto_start: bool,
        default_lr: str, default_dv: str,
    ) -> None:
        super().__init__()
        self.setWindowTitle("PassXMP")
        self.setMinimumSize(760, 560)

        self._presets = PresetsView(registry)
        self._settings = SettingsView(
            lr_path=lr_path, dv_path=dv_path,
            lut_size=lut_size, auto_start=auto_start,
            default_lr=default_lr, default_dv=default_dv,
        )

        self._stack = QStackedWidget()
        self._stack.addWidget(self._presets)    # index 0
        self._stack.addWidget(self._settings)   # index 1

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        root.addWidget(self._stack, 1)

        # Signal wiring
        self._settings.config_changed.connect(self.config_changed.emit)
        self._settings.pause_toggled.connect(self.pause_toggled.emit)
        self._presets.sync_requested.connect(self.sync_requested.emit)
        self._presets.stop_requested.connect(self.stop_requested.emit)

    # ----- header -----

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setStyleSheet(_SEG_STYLE)
        row = QHBoxLayout(header)
        row.setContentsMargins(12, 8, 12, 8)

        title = QLabel("<b>PassXMP</b>")
        row.addWidget(title)
        row.addStretch()

        self._seg = QButtonGroup(self)
        self._seg.setExclusive(True)

        seg_container = QWidget()
        seg_container.setObjectName("SegContainer")
        seg_row = QHBoxLayout(seg_container)
        seg_row.setContentsMargins(0, 0, 0, 0)
        seg_row.setSpacing(0)

        self._btn_presets = QPushButton("Presets")
        self._btn_presets.setCheckable(True)
        self._btn_presets.setChecked(True)
        self._btn_presets.clicked.connect(lambda: self.select_tab("Presets"))
        seg_row.addWidget(self._btn_presets)
        self._seg.addButton(self._btn_presets, 0)

        self._btn_settings = QPushButton("Settings")
        self._btn_settings.setCheckable(True)
        self._btn_settings.clicked.connect(lambda: self.select_tab("Settings"))
        seg_row.addWidget(self._btn_settings)
        self._seg.addButton(self._btn_settings, 1)

        row.addWidget(seg_container)
        return header

    # ----- public API -----

    def select_tab(self, name: str) -> None:
        if name == "Presets":
            self._btn_presets.setChecked(True)
            self._stack.setCurrentIndex(0)
        elif name == "Settings":
            self._btn_settings.setChecked(True)
            self._stack.setCurrentIndex(1)

    def current_tab_name(self) -> str:
        return "Presets" if self._stack.currentIndex() == 0 else "Settings"

    def segmented_control(self) -> QButtonGroup:
        return self._seg

    def presets_view(self) -> PresetsView:
        return self._presets

    def settings_view(self) -> SettingsView:
        return self._settings
