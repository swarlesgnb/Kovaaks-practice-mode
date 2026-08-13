from PyQt6 import QtCore, QtGui, QtWidgets


class CalibrationOverlay(QtWidgets.QWidget):
    """Full-client-area overlay for drag-selecting the score regions to cover.

    Enter = save regions, Ctrl+Z = undo last box, Esc = cancel (clears regions).
    """

    finished = QtCore.pyqtSignal(list)  # list of {x, y, w, h} fractions

    def __init__(self, client_rect):
        super().__init__()
        self.client_x, self.client_y, self.client_w, self.client_h = client_rect

        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.Tool
        )
        self.setGeometry(self.client_x, self.client_y, self.client_w, self.client_h)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self.rects = []
        self.dragging = False
        self.start_pos = None
        self.current_rect = None

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.dragging = True
            self.start_pos = event.position().toPoint()
            self.current_rect = QtCore.QRect(self.start_pos, self.start_pos)
            self.update()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.current_rect = QtCore.QRect(self.start_pos, event.position().toPoint()).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.dragging and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.dragging = False
            if self.current_rect and self.current_rect.width() > 5 and self.current_rect.height() > 5:
                self.rects.append(self.current_rect)
            self.current_rect = None
            self.update()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            self._finish(save=True)
        elif key == QtCore.Qt.Key.Key_Z and event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            if self.rects:
                self.rects.pop()
                self.update()
        elif key == QtCore.Qt.Key.Key_Escape:
            self._finish(save=False)

    def _finish(self, save):
        fractions = []
        if save:
            for r in self.rects:
                fractions.append(
                    {
                        "x": r.x() / self.client_w,
                        "y": r.y() / self.client_h,
                        "w": r.width() / self.client_w,
                        "h": r.height() / self.client_h,
                    }
                )
        self.finished.emit(fractions)
        self.close()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 90))
        painter.setPen(QtGui.QPen(QtGui.QColor(80, 220, 140), 2))
        painter.setBrush(QtGui.QColor(80, 220, 140, 60))
        for r in self.rects:
            painter.drawRect(r)
        if self.current_rect:
            painter.drawRect(self.current_rect)

        painter.setPen(QtGui.QColor(255, 255, 255))
        painter.drawText(
            20, 30,
            "Drag boxes over the score / high-score areas. Enter = save, Ctrl+Z = undo, Esc = cancel",
        )
        painter.end()
