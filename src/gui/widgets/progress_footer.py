"""Progress footer for the Presets view — swaps between idle and active states."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QStackedWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QPushButton,
)


def _format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    return f"{n / (1024 * 1024 * 1024):.2f} GB"


class ProgressFooter(QWidget):
    sync_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._selection_count = 0

        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._build_idle())
        self._stack.addWidget(self._build_active())
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._stack)
        self.setContentsMargins(0, 0, 0, 0)
        self._stack.setCurrentIndex(0)
        self.setStyleSheet(
            "ProgressFooter { border-top: 1px solid palette(mid); }"
        )

    # ----- idle -----

    def _build_idle(self) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(14, 10, 14, 10)
        self._idle_summary = QLabel("Ready")
        self._idle_summary.setStyleSheet("color: palette(placeholder-text);")
        row.addWidget(self._idle_summary, 1)
        self._sync_btn = QPushButton("Sync")
        self._sync_btn.setDefault(True)
        self._sync_btn.clicked.connect(self.sync_clicked.emit)
        self._sync_btn.setEnabled(False)
        row.addWidget(self._sync_btn)
        return w

    # ----- active -----

    def _build_active(self) -> QWidget:
        w = QWidget()
        col = QVBoxLayout(w)
        col.setContentsMargins(14, 10, 14, 10)

        top = QHBoxLayout()
        self._active_title = QLabel("")
        top.addWidget(self._active_title, 1)
        self._active_count = QLabel("")
        self._active_count.setStyleSheet(
            "color: palette(placeholder-text); font-family: ui-monospace, SFMono-Regular, Menlo, monospace;"
        )
        top.addWidget(self._active_count)
        col.addLayout(top)

        mid = QHBoxLayout()
        self._bar = QProgressBar()
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        mid.addWidget(self._bar, 1)
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setStyleSheet("color: #c7352a;")
        self._stop_btn.clicked.connect(self.stop_clicked.emit)
        mid.addWidget(self._stop_btn)
        col.addLayout(mid)

        self._active_bytes = QLabel("")
        self._active_bytes.setStyleSheet("color: palette(placeholder-text);")
        col.addWidget(self._active_bytes)
        return w

    # ----- public API -----

    def is_idle(self) -> bool:
        return self._stack.currentIndex() == 0

    def sync_button(self) -> QPushButton:
        return self._sync_btn

    def stop_button(self) -> QPushButton:
        return self._stop_btn

    def set_selection_count(self, n: int) -> None:
        self._selection_count = n
        self._sync_btn.setText(self.sync_button_label())
        self._sync_btn.setEnabled(n > 0)

    def sync_button_label(self) -> str:
        if self._selection_count <= 0:
            return "Sync"
        return f"Sync {self._selection_count} selected"

    def sync_button_enabled(self) -> bool:
        return self._sync_btn.isEnabled()

    def set_idle(self, last_sync_iso: str | None, selected_count: int) -> None:
        self.set_selection_count(selected_count)
        parts = ["Ready"]
        if last_sync_iso:
            parts.append(f"last sync {last_sync_iso}")
        self._idle_summary.setText(" · ".join(parts))
        self._stack.setCurrentIndex(0)

    def set_active(
        self,
        current_name: str,
        folder: str,
        current_index: int,
        total: int,
        bytes_written: int,
        bytes_projected: int | None = None,
    ) -> None:
        folder_tail = f" · {folder}" if folder else ""
        self._active_title.setText(f"<b>{current_name}</b><span style='color:gray'>{folder_tail}</span>")
        self._active_count.setText(f"{current_index} / {total}")
        self._bar.setRange(0, max(total, 1))
        self._bar.setValue(min(current_index, total))
        bytes_line = f"{_format_bytes(bytes_written)} written"
        if bytes_projected is not None and bytes_projected > 0:
            bytes_line += f" · ~{_format_bytes(bytes_projected)} projected"
        self._active_bytes.setText(bytes_line)
        self._stack.setCurrentIndex(1)
