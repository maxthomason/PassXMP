"""Settings tab — Folders + Sync sections."""

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
    QRadioButton, QButtonGroup, QCheckBox, QFileDialog, QHBoxLayout,
)

from .widgets.live_dot import LiveDot


_SECTION_STYLE = (
    "text-transform: uppercase; font-size: 10.5px; letter-spacing: 0.5px; "
    "color: #8e8e93; margin-top: 8px;"
)
_PATH_STYLE = (
    "color: #6c6c70; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; "
    "font-size: 11.5px;"
)


class SettingsView(QWidget):
    config_changed = pyqtSignal(str, str, int, bool)  # lr, dv, size, auto_start
    pause_toggled = pyqtSignal(bool)                  # True = now paused

    def __init__(
        self,
        lr_path: str, dv_path: str,
        lut_size: int, auto_start: bool,
        default_lr: str, default_dv: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._default_lr = default_lr
        self._default_dv = default_dv
        self._watcher_running = True

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(6)

        # FOLDERS
        root.addWidget(self._section_label("Folders"))
        self._folders_grid = QGridLayout()
        self._folders_grid.setHorizontalSpacing(12)
        self._folders_grid.setVerticalSpacing(6)
        self._lr_edit = self._add_path_row(self._folders_grid, 0, "Lightroom Presets", lr_path)
        self._dv_edit = self._add_path_row(self._folders_grid, 1, "DaVinci LUT", dv_path)
        root.addLayout(self._folders_grid)

        # SYNC
        root.addWidget(self._section_label("Sync"))
        sync_grid = QGridLayout()
        sync_grid.setHorizontalSpacing(12)
        sync_grid.setVerticalSpacing(8)

        sync_grid.addWidget(QLabel("LUT precision"), 0, 0)
        self._radio_33 = QRadioButton("33³")
        self._radio_65 = QRadioButton("65³")
        self._size_group = QButtonGroup(self)
        self._size_group.addButton(self._radio_33, 33)
        self._size_group.addButton(self._radio_65, 65)
        if lut_size == 65:
            self._radio_65.setChecked(True)
        else:
            self._radio_33.setChecked(True)
        self._radio_33.toggled.connect(lambda _c: self._emit_config())
        self._radio_65.toggled.connect(lambda _c: self._emit_config())
        radio_row = QHBoxLayout()
        radio_row.addWidget(self._radio_33)
        radio_row.addWidget(self._radio_65)
        radio_row.addStretch()
        sync_grid.addLayout(radio_row, 0, 1, 1, 2)

        sync_grid.addWidget(QLabel("Start on launch"), 1, 0)
        self._auto_start_cb = QCheckBox("")
        self._auto_start_cb.setChecked(auto_start)
        self._auto_start_cb.toggled.connect(lambda _c: self._emit_config())
        sync_grid.addWidget(self._auto_start_cb, 1, 1, 1, 2)

        watcher_row = QHBoxLayout()
        self._watcher_dot = LiveDot()
        watcher_row.addWidget(self._watcher_dot)
        watcher_row.addWidget(QLabel("Watcher"))
        watcher_row.addStretch()
        watcher_w = QWidget()
        watcher_w.setLayout(watcher_row)
        sync_grid.addWidget(watcher_w, 2, 0, 1, 2)
        self._watcher_btn = QPushButton("Pause")
        self._watcher_btn.clicked.connect(self._on_watcher_click)
        sync_grid.addWidget(self._watcher_btn, 2, 2)

        root.addLayout(sync_grid)
        root.addStretch()

    # ----- helpers -----

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(_SECTION_STYLE)
        return label

    def _add_path_row(self, grid: QGridLayout, row: int, label: str, value: str) -> QLineEdit:
        grid.addWidget(QLabel(label), row, 0)
        edit = QLineEdit(value)
        edit.setReadOnly(True)
        edit.setStyleSheet(_PATH_STYLE)
        edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(edit, row, 1)
        btn = QPushButton("Choose…")
        btn.clicked.connect(lambda: self._choose_dir(edit))
        grid.addWidget(btn, row, 2)
        return edit

    def _choose_dir(self, edit: QLineEdit) -> None:
        start = edit.text().strip() or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, "Select Folder", start)
        if path:
            edit.setText(path)
            self._emit_config()

    def _on_watcher_click(self) -> None:
        now_paused = self._watcher_running  # about to flip
        self._watcher_running = not self._watcher_running
        self._watcher_dot.set_running(self._watcher_running)
        self._watcher_btn.setText("Pause" if self._watcher_running else "Resume")
        self.pause_toggled.emit(now_paused)

    def _emit_config(self) -> None:
        self.config_changed.emit(
            self.lr_path(), self.dv_path(),
            self.lut_size(), self.auto_start(),
        )

    # ----- public getters -----

    def lr_path(self) -> str: return self._lr_edit.text().strip()
    def dv_path(self) -> str: return self._dv_edit.text().strip()
    def lut_size(self) -> int: return self._size_group.checkedId() or 33
    def auto_start(self) -> bool: return self._auto_start_cb.isChecked()

    def watcher_dot(self) -> LiveDot: return self._watcher_dot
    def watcher_button(self) -> QPushButton: return self._watcher_btn

    def set_watcher_running(self, running: bool) -> None:
        self._watcher_running = running
        self._watcher_dot.set_running(running)
        self._watcher_btn.setText("Pause" if running else "Resume")
