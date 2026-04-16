"""Small pulsing green-dot widget for live-state indicators."""

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget


_DOT_DIAMETER = 7
_HALO_MAX = 6
_WIDGET_SIZE = _DOT_DIAMETER + _HALO_MAX * 2
_RUNNING_COLOR = QColor(50, 199, 89)
_PAUSED_COLOR = QColor(161, 161, 166)


class LiveDot(QWidget):
    """A 7 px solid dot with an animated pulsing halo.

    When running: green dot, halo radius cycles 0 -> 6 px every 1.8 s.
    When paused: grey dot, no halo.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(_WIDGET_SIZE, _WIDGET_SIZE)
        self._halo = 0.0
        self._running = True

        self._anim = QPropertyAnimation(self, b"halo")
        self._anim.setDuration(1800)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(float(_HALO_MAX))
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim.setLoopCount(-1)
        self._anim.start()

    def _get_halo(self) -> float:
        return self._halo

    def _set_halo(self, value: float) -> None:
        self._halo = value
        self.update()

    halo = pyqtProperty(float, fget=_get_halo, fset=_set_halo)

    def is_running(self) -> bool:
        return self._running

    def set_running(self, running: bool) -> None:
        if running == self._running:
            return
        self._running = running
        if running:
            self._anim.start()
        else:
            self._anim.stop()
            self._halo = 0.0
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = cy = _WIDGET_SIZE / 2
        color = _RUNNING_COLOR if self._running else _PAUSED_COLOR

        if self._running and self._halo > 0:
            halo_color = QColor(color)
            progress = self._halo / _HALO_MAX
            halo_color.setAlphaF(max(0.0, 0.55 * (1.0 - progress)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(halo_color)
            r = _DOT_DIAMETER / 2 + self._halo
            painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        r = _DOT_DIAMETER / 2
        painter.drawEllipse(int(cx - r), int(cy - r), _DOT_DIAMETER, _DOT_DIAMETER)
