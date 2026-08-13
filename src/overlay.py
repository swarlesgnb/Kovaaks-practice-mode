from PyQt6 import QtCore, QtGui, QtWidgets
import win32con
import win32gui

from . import window_finder


class OverlayWindow(QtWidgets.QWidget):
    """Always-on-top, click-through window that draws cover boxes over the
    calibrated score regions, tracking the KovaaK's window as it moves/resizes."""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._client_rect = None
        self._click_through_applied = False

        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(50)

        # A single HWND_TOPMOST call loses to KovaaK's own z-order
        # reassertion the moment it's the active fullscreen window — Windows
        # appears to keep it in an optimized presentation mode that steady,
        # low-frequency reassertion can't break. A short, rapid burst right
        # when the overlay becomes visible reliably knocks it out of that
        # mode; the regular refresh timer's slower reassertion is then
        # enough to hold the position.
        self._burst_timer = QtCore.QTimer(self)
        self._burst_timer.setInterval(30)
        self._burst_timer.timeout.connect(self._reassert_topmost)
        self._burst_ticks_left = 0

    def refresh(self):
        hwnd = window_finder.find_kovaaks_window()
        if not hwnd or not self.config.practice_mode_enabled:
            if self.isVisible():
                self.hide()
            self._burst_timer.stop()
            self._client_rect = None
            return

        rect = window_finder.get_client_screen_rect(hwnd)
        if rect != self._client_rect:
            self._client_rect = rect
            x, y, w, h = rect
            self.setGeometry(x, y, w, h)

        was_visible = self.isVisible()
        if not was_visible:
            self.show()

        if not self._click_through_applied:
            self._make_click_through()

        if not was_visible:
            self._start_topmost_burst()

        self._reassert_topmost()
        self.update()

    def _start_topmost_burst(self):
        self._burst_ticks_left = 70  # ~2.1s at 30ms/tick
        self._burst_timer.start()

    def _reassert_topmost(self):
        if self._burst_ticks_left > 0:
            self._burst_ticks_left -= 1
            if self._burst_ticks_left == 0:
                self._burst_timer.stop()

        hwnd = int(self.winId())
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOPMOST,
            0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
        )

    def _reassert_topmost(self):
        hwnd = int(self.winId())
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOPMOST,
            0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
        )

    def _make_click_through(self):
        hwnd = int(self.winId())
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(
            hwnd,
            win32con.GWL_EXSTYLE,
            ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_NOACTIVATE,
        )
        self._click_through_applied = True

    def paintEvent(self, event):
        if not self._client_rect:
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        label = self.config.data.get("cover_label", "PRACTICE MODE")

        for region in self.config.regions:
            rx = region["x"] * w
            ry = region["y"] * h
            rw = region["w"] * w
            rh = region["h"] * h
            rect = QtCore.QRectF(rx, ry, rw, rh)

            painter.setBrush(QtGui.QColor(12, 12, 16, 235))
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 60), 1))
            painter.drawRoundedRect(rect, 6, 6)

            font = painter.font()
            font.setPointSizeF(max(7.0, rh * 0.22))
            painter.setFont(font)
            painter.setPen(QtGui.QColor(190, 190, 200, 210))
            painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, label)
        painter.end()
