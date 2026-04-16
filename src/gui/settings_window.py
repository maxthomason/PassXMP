"""Settings window for editing paths and options."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QRadioButton, QButtonGroup,
    QCheckBox, QFrame, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont


class SettingsWindow(QWidget):
    """Settings/preferences editor."""

    settings_saved = pyqtSignal(str, str, int, bool)  # lr, dv, size, auto_start

    def __init__(self, lr_path: str, dv_path: str, lut_size: int, auto_start: bool):
        super().__init__()
        self.setWindowTitle("PassXMP — Settings")
        self.setFixedSize(520, 380)
        self._init_ui(lr_path, dv_path, lut_size, auto_start)

    def _init_ui(self, lr_path: str, dv_path: str, lut_size: int, auto_start: bool) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(28, 20, 28, 20)

        title = QLabel("Settings")
        title.setFont(QFont("", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #e5e7eb;")
        layout.addWidget(line)

        # Lightroom path
        lr_label = QLabel("Lightroom Presets Folder")
        lr_label.setFont(QFont("", 11, QFont.Weight.DemiBold))
        layout.addWidget(lr_label)

        lr_row = QHBoxLayout()
        self._lr_edit = QLineEdit(lr_path)
        lr_row.addWidget(self._lr_edit)
        lr_browse = QPushButton("Browse...")
        lr_browse.clicked.connect(self._browse_lr)
        lr_row.addWidget(lr_browse)
        layout.addLayout(lr_row)

        # DaVinci path
        dv_label = QLabel("DaVinci LUT Folder")
        dv_label.setFont(QFont("", 11, QFont.Weight.DemiBold))
        layout.addWidget(dv_label)

        dv_row = QHBoxLayout()
        self._dv_edit = QLineEdit(dv_path)
        dv_row.addWidget(self._dv_edit)
        dv_browse = QPushButton("Browse...")
        dv_browse.clicked.connect(self._browse_dv)
        dv_row.addWidget(dv_browse)
        layout.addLayout(dv_row)

        # LUT size
        size_label = QLabel("LUT Size")
        size_label.setFont(QFont("", 11, QFont.Weight.DemiBold))
        layout.addWidget(size_label)

        size_row = QHBoxLayout()
        self._size_group = QButtonGroup(self)
        self._radio_33 = QRadioButton("33 (standard)")
        self._radio_65 = QRadioButton("65 (high quality)")
        if lut_size == 65:
            self._radio_65.setChecked(True)
        else:
            self._radio_33.setChecked(True)
        self._size_group.addButton(self._radio_33, 33)
        self._size_group.addButton(self._radio_65, 65)
        size_row.addWidget(self._radio_33)
        size_row.addWidget(self._radio_65)
        size_row.addStretch()
        layout.addLayout(size_row)

        # Auto-start checkbox
        self._auto_start_cb = QCheckBox("Start syncing automatically on launch")
        self._auto_start_cb.setChecked(auto_start)
        layout.addWidget(self._auto_start_cb)

        layout.addStretch()

        # Save / Cancel
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.clicked.connect(self.close)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(36)
        save_btn.setStyleSheet(
            "QPushButton { background-color: #2563eb; color: white; "
            "border-radius: 6px; font-weight: bold; padding: 0 24px; }"
            "QPushButton:hover { background-color: #1d4ed8; }"
        )
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _browse_lr(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select Lightroom Presets Folder", self._lr_edit.text()
        )
        if path:
            self._lr_edit.setText(path)

    def _browse_dv(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select DaVinci LUT Folder", self._dv_edit.text()
        )
        if path:
            self._dv_edit.setText(path)

    def _on_save(self) -> None:
        lr = self._lr_edit.text().strip()
        dv = self._dv_edit.text().strip()
        if not lr or not dv:
            QMessageBox.warning(self, "Missing Paths",
                                "Both paths must be specified.")
            return
        size = self._size_group.checkedId()
        auto = self._auto_start_cb.isChecked()
        self.settings_saved.emit(lr, dv, size, auto)
        self.close()
