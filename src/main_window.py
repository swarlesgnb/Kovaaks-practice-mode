from PyQt6 import QtCore, QtGui, QtWidgets

from . import window_finder
from .calibration import CalibrationOverlay
from .hotkey import HotkeyBridge
from .icons import build_icon
from .tray import TrayController

WINDOW_STYLE = """
QWidget#root { background-color: #1b1c22; }
QLabel { color: #d8d8e0; }
QLabel#title { font-size: 18px; font-weight: 700; color: #ffffff; }
QLabel#subtitle { color: #9a9aa8; }
QLabel#status { color: #9a9aa8; }
QLabel#banner {
    background-color: #2a2410;
    border: 1px solid #6b5a1a;
    border-radius: 6px;
    padding: 10px;
    color: #e8d488;
}
QLabel#footer { color: #6f6f7c; font-size: 11px; }
QPushButton#toggleOff {
    background-color: #33343d; color: #e8e8f0; border: none;
    border-radius: 8px; padding: 16px; font-size: 15px; font-weight: 600;
}
QPushButton#toggleOff:hover { background-color: #3d3e48; }
QPushButton#toggleOn {
    background-color: #4fd18c; color: #10241a; border: none;
    border-radius: 8px; padding: 16px; font-size: 15px; font-weight: 600;
}
QPushButton#toggleOn:hover { background-color: #63d99a; }
QPushButton#secondary {
    background-color: transparent; color: #c9c9d4;
    border: 1px solid #45454f; border-radius: 6px; padding: 8px 12px;
}
QPushButton#secondary:hover { background-color: #2a2b33; }
QFrame#sep { background-color: #303138; max-height: 1px; }
"""


class MainWindow(QtWidgets.QWidget):
    def __init__(self, config, overlay):
        super().__init__()
        self.config = config
        self.overlay = overlay
        self._calibration_window = None

        self.setObjectName("root")
        self.setWindowTitle("KovaaK's Practice Mode")
        self.setWindowIcon(build_icon(True))
        self.setFixedWidth(420)
        self.setStyleSheet(WINDOW_STYLE)

        self._build_ui()

        self.tray = TrayController(self.config, self.start_calibration, self.show_and_raise)
        self.hotkey = HotkeyBridge(self.config.hotkey)
        self.hotkey.triggered.connect(lambda: self.tray.set_enabled(not self.config.practice_mode_enabled))
        try:
            self.hotkey.start()
        except Exception:
            pass  # hotkey is a convenience; the button/tray toggle still work without it

        self._poll_timer = QtCore.QTimer(self)
        self._poll_timer.timeout.connect(self._refresh_status)
        self._poll_timer.start(300)
        self._refresh_status()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("KovaaK's Practice Mode")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QtWidgets.QLabel("Hide your score, high score, and rank so a session is about improving, not chasing a number.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.status_label = QtWidgets.QLabel("Checking for KovaaK's...")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)

        self.toggle_button = QtWidgets.QPushButton()
        self.toggle_button.setObjectName("toggleOff")
        self.toggle_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.toggle_button.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self.toggle_button)

        sep1 = QtWidgets.QFrame()
        sep1.setObjectName("sep")
        layout.addWidget(sep1)

        calib_label = QtWidgets.QLabel("Score regions")
        calib_label.setObjectName("subtitle")
        layout.addWidget(calib_label)

        self.regions_label = QtWidgets.QLabel()
        self.regions_label.setWordWrap(True)
        layout.addWidget(self.regions_label)

        calib_row = QtWidgets.QHBoxLayout()
        self.calibrate_button = QtWidgets.QPushButton("Calibrate Score Regions...")
        self.calibrate_button.setObjectName("secondary")
        self.calibrate_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.calibrate_button.clicked.connect(self.start_calibration)
        calib_row.addWidget(self.calibrate_button)

        self.clear_button = QtWidgets.QPushButton("Clear")
        self.clear_button.setObjectName("secondary")
        self.clear_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.clear_button.clicked.connect(self._on_clear_regions)
        calib_row.addWidget(self.clear_button)
        layout.addLayout(calib_row)

        sep2 = QtWidgets.QFrame()
        sep2.setObjectName("sep")
        layout.addWidget(sep2)

        banner = QtWidgets.QLabel(
            "KovaaK's must be set to Windowed Fullscreen (not Fullscreen), or Windows "
            "will hide the cover boxes. In KovaaK's: Settings → Video → Display Mode."
        )
        banner.setObjectName("banner")
        banner.setWordWrap(True)
        layout.addWidget(banner)

        footer = QtWidgets.QLabel(
            f"Hotkey: {self.config.hotkey}  •  Closing this window keeps running in the "
            "system tray — right-click the tray icon to Quit."
        )
        footer.setObjectName("footer")
        footer.setWordWrap(True)
        layout.addWidget(footer)

    def _refresh_status(self):
        hwnd = window_finder.find_kovaaks_window()
        self.status_label.setText(
            "● KovaaK's detected" if hwnd else "○ KovaaK's not running"
        )

        enabled = self.config.practice_mode_enabled
        self.toggle_button.setObjectName("toggleOn" if enabled else "toggleOff")
        self.toggle_button.setText(
            "Practice Mode is ON — scores hidden" if enabled else "Turn Practice Mode ON"
        )
        # Re-polish so the new objectName's stylesheet rule takes effect.
        self.toggle_button.style().unpolish(self.toggle_button)
        self.toggle_button.style().polish(self.toggle_button)

        count = len(self.config.regions)
        self.regions_label.setText(
            "No regions calibrated yet — practice mode won't hide anything until you calibrate."
            if count == 0
            else f"{count} region{'s' if count != 1 else ''} calibrated."
        )

    def _on_toggle_clicked(self):
        self.tray.set_enabled(not self.config.practice_mode_enabled)
        self._refresh_status()

    def _on_clear_regions(self):
        if not self.config.regions:
            return
        confirm = QtWidgets.QMessageBox.question(
            self, "Clear Score Regions", "Remove all calibrated regions?"
        )
        if confirm == QtWidgets.QMessageBox.StandardButton.Yes:
            self.config.set_regions([])
            self._refresh_status()

    def start_calibration(self):
        hwnd = window_finder.find_kovaaks_window()
        if not hwnd:
            QtWidgets.QMessageBox.warning(
                self,
                "KovaaK's Practice Mode",
                "Couldn't find a running KovaaK's window. Launch the game first, then calibrate.",
            )
            return

        rect = window_finder.get_client_screen_rect(hwnd)
        calibration_window = CalibrationOverlay(rect)

        def on_finished(fractions):
            if fractions:
                self.config.set_regions(fractions)
            self._refresh_status()
            self._calibration_window = None

        calibration_window.finished.connect(on_finished)
        calibration_window.show()
        calibration_window.activateWindow()
        self._calibration_window = calibration_window  # keep alive while in use

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        # Closing the window minimizes to tray instead of quitting; Quit is
        # only reachable via the tray menu, matching typical tray-app behavior.
        event.ignore()
        self.hide()
        self.tray.tray.showMessage(
            "KovaaK's Practice Mode",
            "Still running in the tray. Right-click the tray icon to quit.",
            QtWidgets.QSystemTrayIcon.MessageIcon.Information,
            2000,
        )
