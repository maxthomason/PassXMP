"""First-launch setup screen for configuring Lightroom and DaVinci paths."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QRadioButton, QButtonGroup,
    QMessageBox, QFrame,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont


class SetupWindow(QWidget):
    """Setup wizard shown on first launch."""

    setup_complete = pyqtSignal(str, str, int)  # lr_path, dv_path, lut_size

    def __init__(self, detected_lr: str = "", detected_dv: str = ""):
        super().__init__()
        self.setWindowTitle("PassXMP — Setup")
        self.setFixedSize(560, 380)
        self._init_ui(detected_lr, detected_dv)

    def _init_ui(self, detected_lr: str, detected_dv: str) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 24, 32, 24)

        # Title
        title = QLabel("PassXMP")
        title.setFont(QFont("", 22, QFont.Weight.Bold))
        layout.addWidget(title)

        subtitle = QLabel("Your Lightroom presets, instantly in DaVinci.")
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #ddd;")
        layout.addWidget(line)

        # Lightroom path
        lr_label = QLabel("Lightroom Presets Folder")
        lr_label.setFont(QFont("", 11, QFont.Weight.DemiBold))
        layout.addWidget(lr_label)

        lr_row = QHBoxLayout()
        self._lr_edit = QLineEdit(detected_lr)
        self._lr_edit.setPlaceholderText("Select your Lightroom presets folder...")
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
        self._dv_edit = QLineEdit(detected_dv)
        self._dv_edit.setPlaceholderText("Select your DaVinci Resolve LUT folder...")
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
        self._radio_33.setChecked(True)
        self._size_group.addButton(self._radio_33, 33)
        self._size_group.addButton(self._radio_65, 65)
        size_row.addWidget(self._radio_33)
        size_row.addWidget(self._radio_65)
        size_row.addStretch()
        layout.addLayout(size_row)

        layout.addStretch()

        # Start button
        self._start_btn = QPushButton("Start Syncing")
        self._start_btn.setFixedHeight(40)
        self._start_btn.setStyleSheet(
            "QPushButton { background-color: #2563eb; color: white; "
            "border-radius: 6px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1d4ed8; }"
        )
        self._start_btn.clicked.connect(self._on_start)
        layout.addWidget(self._start_btn)

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

    def _on_start(self) -> None:
        lr = self._lr_edit.text().strip()
        dv = self._dv_edit.text().strip()

        if not lr or not dv:
            QMessageBox.warning(
                self, "Missing Paths",
                "Please select both a Lightroom presets folder and a DaVinci LUT folder."
            )
            return

        import os
        if not os.path.isdir(lr):
            QMessageBox.warning(
                self, "Invalid Path",
                f"Lightroom presets folder not found:\n{lr}"
            )
            return

        if not os.path.isdir(dv):
            # Offer to create it
            reply = QMessageBox.question(
                self, "Create Folder?",
                f"DaVinci LUT folder does not exist:\n{dv}\n\nCreate it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    os.makedirs(dv, exist_ok=True)
                except OSError as e:
                    QMessageBox.critical(self, "Error", f"Could not create folder:\n{e}")
                    return
            else:
                return

        lut_size = self._size_group.checkedId()
        self.setup_complete.emit(lr, dv, lut_size)
