from PyQt6 import QtCore, QtGui, QtWidgets
import win32api
import win32con
import win32gui

from . import input_state, window_finder
from .run_tracker import RunCompletionTracker

MONITOR_DEFAULTTONEAREST = 2

# Cover box styling. ACCENT matches the app's green so the covers read as
# part of the same tool rather than anonymous black rectangles.
ACCENT = (79, 209, 140)
RADIUS = 10
LABEL_MIN_PT = 8.0
LABEL_MAX_PT = 22.0
MIN_LABEL_HEIGHT = 42
MIN_LABEL_WIDTH = 90


def _covered_by_foreground(hwnd):
    """True if the foreground window is likely covering KovaaK's - i.e. it's
    a different window on the same monitor. A foreground window on a
    *different* monitor doesn't obscure a fullscreen KovaaK's window at all,
    which plain "is KovaaK's focused" can't distinguish on a multi-monitor
    setup. Fails toward False (assume not covered, keep protecting the
    score) if monitor lookup ever fails - worst case that just leaves a
    cover box floating over some other app, rather than silently exposing
    the score."""
    fg = win32gui.GetForegroundWindow()
    if fg == hwnd:
        return False
    try:
        return win32api.MonitorFromWindow(fg, MONITOR_DEFAULTTONEAREST) == win32api.MonitorFromWindow(
            hwnd, MONITOR_DEFAULTTONEAREST
        )
    except Exception:
        return False


def _point_in_region(x, y, region, client_rect):
    cx, cy, cw, ch = client_rect
    rx = cx + region["x"] * cw
    ry = cy + region["y"] * ch
    rw = region["w"] * cw
    rh = region["h"] * ch
    return rx <= x <= rx + rw and ry <= y <= ry + rh


class OverlayWindow(QtWidgets.QWidget):
    """Always-on-top, click-through window that draws cover boxes over the
    calibrated score regions, tracking the KovaaK's window as it moves/resizes."""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._client_rect = None
        self._click_through_applied = False
        self._run_tracker = RunCompletionTracker()
        self._was_aiming = False
        self._click_tracker = input_state.ClickTracker()

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
        # reassertion the moment it's the active fullscreen window. Windows
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
        # Polled every tick unconditionally (even while hidden/aiming) so
        # the tracker's button-state stays accurate; only acted on below.
        click_pos = self._click_tracker.poll()

        hwnd = window_finder.find_kovaaks_window()
        if not hwnd or not self.config.practice_mode_enabled:
            if self.isVisible():
                self.hide()
            self._burst_timer.stop()
            self._client_rect = None
            return

        if _covered_by_foreground(hwnd):
            # Something else is now on top of KovaaK's on its own monitor
            # (you've alt-tabbed to an app sharing that screen). A window
            # focused on a *different* monitor doesn't affect this - a
            # fullscreen KovaaK's stays fully visible there regardless.
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

        if input_state.is_actively_aiming(rect):
            # Mid-run: don't obstruct the view. KovaaK's hides and confines
            # the cursor to its window while aiming, and releases it in
            # menus/results - a reliable "actively playing" signal without
            # reading game memory or pixels.
            self._was_aiming = True
            if self.isVisible():
                self.hide()
            self._burst_timer.stop()
            return

        if self._was_aiming:
            # Aiming just stopped - a run may have ended this instant.
            # Force a fresh read instead of possibly using a check from up
            # to a second ago, so the cover doesn't lag behind the actual
            # completion.
            self._was_aiming = False
            self._run_tracker.force_recheck()

        if click_pos and any(
            _point_in_region(click_pos[0], click_pos[1], region, rect)
            for region in self.config.trigger_regions
        ):
            # Clicked a calibrated button zone (Play/Next/Replay/scenario
            # list) - you've moved on, no need to wait out the fallback
            # timeout. Position-based, so a click on a second monitor can
            # never match a zone calibrated against this monitor's window.
            self._run_tracker.dismiss()

        self._run_tracker.set_perf_dir(window_finder.get_performances_dir(hwnd))
        if not self._run_tracker.should_show_results():
            # Not aiming, but also not just off a run - you're browsing
            # scenarios/menus, not looking at a score. Only cover the short
            # window right after a run completes, not every non-aiming
            # moment, so picking a new scenario isn't half-obstructed.
            if self.isVisible():
                self.hide()
            self._burst_timer.stop()
            return

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
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)
        w, h = self.width(), self.height()
        label = self.config.data.get("cover_label", "PRACTICE MODE")

        for region in self.config.regions:
            rect = QtCore.QRectF(
                region["x"] * w, region["y"] * h, region["w"] * w, region["h"] * h
            )
            self._paint_cover(painter, rect, label)
        painter.end()

    def _paint_cover(self, painter, rect, label):
        radius = min(RADIUS, rect.width() / 3, rect.height() / 3)

        # Fully opaque throughout - a gradient reads as depth without ever
        # letting the score bleed through, which defeats the whole point.
        gradient = QtGui.QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0.0, QtGui.QColor(31, 33, 42))
        gradient.setColorAt(1.0, QtGui.QColor(18, 19, 25))
        painter.setBrush(gradient)
        painter.setPen(QtGui.QPen(QtGui.QColor(*ACCENT, 70), 1))
        painter.drawRoundedRect(rect, radius, radius)

        # Inset hairline: catches the light along the top edge so large
        # panels don't read as flat dead rectangles.
        inner = rect.adjusted(1, 1, -1, -1)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 12), 1))
        painter.drawRoundedRect(inner, max(0.0, radius - 1), max(0.0, radius - 1))

        if rect.height() < MIN_LABEL_HEIGHT or rect.width() < MIN_LABEL_WIDTH:
            # Too small to letter-space a label into without it looking
            # cramped or clipping; the plain panel reads better.
            return

        font = painter.font()
        font.setPointSizeF(
            max(LABEL_MIN_PT, min(LABEL_MAX_PT, rect.height() * 0.16, rect.width() * 0.075))
        )
        font.setWeight(QtGui.QFont.Weight.DemiBold)
        font.setLetterSpacing(QtGui.QFont.SpacingType.PercentageSpacing, 118)
        painter.setFont(font)

        metrics = QtGui.QFontMetricsF(font)
        text = label.upper()
        text_w = metrics.horizontalAdvance(text)
        if text_w > rect.width() - 16:
            return  # would clip or crowd the edges

        painter.setPen(QtGui.QColor(150, 154, 168))
        painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, text)

        # Short accent rule under the label, scaled to the text it sits
        # beneath so it reads as part of the same lockup at any box size.
        rule_w = min(text_w * 0.5, rect.width() * 0.4)
        rule_y = rect.center().y() + metrics.height() * 0.72
        if rule_y < rect.bottom() - 6:
            painter.setPen(QtGui.QPen(QtGui.QColor(*ACCENT, 130), 2))
            painter.drawLine(
                QtCore.QPointF(rect.center().x() - rule_w / 2, rule_y),
                QtCore.QPointF(rect.center().x() + rule_w / 2, rule_y),
            )
