"""Presets tab — topbar, file table, progress footer."""

import os

from PyQt6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, pyqtSignal,
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTableView,
    QHeaderView, QAbstractItemView, QStackedWidget,
)

from ..core.file_registry import FileRegistry, derive_status
from .widgets.live_dot import LiveDot
from .widgets.progress_footer import ProgressFooter
from .widgets.status_cell import STATUS_COLORS, status_display


COL_CHECK = 0
COL_NAME = 1
COL_FOLDER = 2
COL_STATUS = 3


class PresetsTableModel(QAbstractTableModel):
    """Maps a FileRegistry into a 4-column Qt table model."""

    def __init__(self, registry: FileRegistry) -> None:
        super().__init__()
        self._registry = registry
        registry.rows_reset.connect(self._on_rows_reset)
        registry.row_changed.connect(self._on_row_changed)
        registry.row_inserted.connect(self._on_row_inserted)
        registry.row_removed.connect(self._on_row_removed)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else self._registry.row_count()

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else 4

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole or orientation != Qt.Orientation.Horizontal:
            return None
        return ["", "Name", "Folder", "✓"][section]

    def flags(self, index: QModelIndex):
        base = super().flags(index)
        if index.column() == COL_CHECK:
            return base | Qt.ItemFlag.ItemIsUserCheckable
        return base

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self._registry.row_at(index.row())
        status = self._registry.status(row.xmp_path)
        col = index.column()

        if role == Qt.ItemDataRole.CheckStateRole and col == COL_CHECK:
            return Qt.CheckState.Checked.value if row.selected else Qt.CheckState.Unchecked.value

        if role == Qt.ItemDataRole.DisplayRole:
            if col == COL_NAME:
                name = os.path.basename(row.xmp_path)
                if status == "syncing":
                    return f"{name}    syncing…"
                return name
            if col == COL_FOLDER:
                return row.folder
            if col == COL_STATUS:
                glyph, _ = status_display(status)
                return glyph
            return ""

        if role == Qt.ItemDataRole.ForegroundRole:
            if col == COL_FOLDER:
                return STATUS_COLORS["muted"]
            if col == COL_STATUS:
                _, role_name = status_display(status)
                return STATUS_COLORS[role_name]
            if col == COL_NAME and status == "syncing":
                return STATUS_COLORS["muted"]

        if role == Qt.ItemDataRole.TextAlignmentRole and col == COL_STATUS:
            return int(Qt.AlignmentFlag.AlignCenter)

        if role == Qt.ItemDataRole.ToolTipRole:
            if col == COL_STATUS and status == "failed" and row.last_error:
                return row.last_error
            if col == COL_NAME:
                return row.xmp_path
        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if role != Qt.ItemDataRole.CheckStateRole or index.column() != COL_CHECK:
            return False
        row = self._registry.row_at(index.row())
        checked = int(value) == int(Qt.CheckState.Checked.value)
        self._registry.set_selected(row.xmp_path, checked)
        return True

    # ----- registry signal handlers -----

    def _on_rows_reset(self) -> None:
        self.beginResetModel()
        self.endResetModel()

    def _on_row_changed(self, row: int) -> None:
        self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))

    def _on_row_inserted(self, row: int) -> None:
        self.beginInsertRows(QModelIndex(), row, row)
        self.endInsertRows()

    def _on_row_removed(self, row: int) -> None:
        self.beginRemoveRows(QModelIndex(), row, row)
        self.endRemoveRows()


class _NameFilterProxy(QSortFilterProxyModel):
    def __init__(self) -> None:
        super().__init__()
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterKeyColumn(COL_NAME)


class PresetsView(QWidget):
    """Topbar + file table + progress footer."""

    sync_requested = pyqtSignal(list)   # list[FileState]
    stop_requested = pyqtSignal()

    def __init__(self, registry: FileRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._registry = registry

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())
        root.addWidget(self._build_table(), 1)
        root.addWidget(self._build_footer())

        registry.rows_reset.connect(self._refresh_summary)
        registry.row_changed.connect(lambda _i: self._refresh_summary())
        registry.row_inserted.connect(lambda _i: self._refresh_summary())
        registry.row_removed.connect(lambda _i: self._refresh_summary())
        self._refresh_summary()
        self._refresh_empty_state()

    # ----- topbar -----

    def _build_topbar(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            "QWidget { background: palette(alternate-base); }"
        )
        row = QHBoxLayout(w)
        row.setContentsMargins(14, 10, 14, 10)
        self._dot = LiveDot()
        row.addWidget(self._dot)
        self._summary = QLabel("")
        self._summary.setStyleSheet("color: palette(text);")
        row.addWidget(self._summary, 1)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search")
        self._search.setFixedWidth(160)
        self._search.textChanged.connect(self.set_search_text)
        row.addWidget(self._search)
        return w

    # ----- table -----

    def _build_table(self) -> QWidget:
        self._model = PresetsTableModel(self._registry)
        self._proxy = _NameFilterProxy()
        self._proxy.setSourceModel(self._model)

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setHighlightSections(False)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(COL_CHECK, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(COL_CHECK, 28)
        hdr.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(COL_FOLDER, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(COL_STATUS, 36)

        self._empty_label = QLabel("")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            "color: palette(placeholder-text); font-size: 13px; padding: 40px;"
        )
        self._empty_label.setWordWrap(True)

        self._table_stack = QStackedWidget()
        self._table_stack.addWidget(self._table)        # index 0
        self._table_stack.addWidget(self._empty_label)  # index 1

        self._folders_configured = True
        return self._table_stack

    # ----- footer -----

    def _build_footer(self) -> QWidget:
        self._footer = ProgressFooter()
        self._footer.sync_clicked.connect(self._on_sync_clicked)
        self._footer.stop_clicked.connect(self.stop_requested.emit)
        return self._footer

    # ----- public API -----

    def set_search_text(self, text: str) -> None:
        self._proxy.setFilterFixedString(text)
        self._refresh_summary()

    def visible_row_count(self) -> int:
        return self._proxy.rowCount()

    def toggle_all_visible(self, checked: bool) -> None:
        for i in range(self._proxy.rowCount()):
            src = self._proxy.mapToSource(self._proxy.index(i, 0))
            row = self._registry.row_at(src.row())
            self._registry.set_selected(row.xmp_path, checked)

    def summary_text(self) -> str:
        rows = self._registry.rows()
        total = len(rows)
        selected = sum(1 for r in rows if r.selected)
        synced = sum(1 for r in rows if derive_status(r, set(), set()) == "synced")
        failed = sum(1 for r in rows
                     if self._registry.status(r.xmp_path) == "failed")
        parts = [f"{total} presets", f"{selected} selected",
                 f"{synced} synced", f"{failed} failed"]
        return " · ".join(parts)

    def footer(self) -> ProgressFooter:
        return self._footer

    def live_dot(self) -> LiveDot:
        return self._dot

    def set_watcher_running(self, running: bool) -> None:
        self._dot.set_running(running)

    def _on_sync_clicked(self) -> None:
        self.sync_requested.emit(self._registry.selected_rows())

    # ----- empty state -----

    def set_folders_configured(self, ok: bool) -> None:
        self._folders_configured = ok
        self._refresh_empty_state()

    def empty_state_visible(self) -> bool:
        return self._table_stack.currentIndex() == 1

    def empty_state_text(self) -> str:
        return self._empty_label.text()

    def _refresh_empty_state(self) -> None:
        if not self._folders_configured:
            self._empty_label.setText(
                "Choose a Lightroom folder in Settings to get started."
            )
            self._table_stack.setCurrentIndex(1)
        elif self._registry.row_count() == 0:
            self._empty_label.setText(
                "No Lightroom presets found in this folder yet.\n"
                "Create one in Lightroom and it will show up here."
            )
            self._table_stack.setCurrentIndex(1)
        else:
            self._table_stack.setCurrentIndex(0)

    def _refresh_summary(self) -> None:
        self._summary.setText(self.summary_text())
        selected = sum(1 for r in self._registry.rows() if r.selected)
        self._footer.set_selection_count(selected)
        self._refresh_empty_state()
