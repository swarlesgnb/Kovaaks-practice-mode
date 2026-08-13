from PyQt6 import QtCore, QtGui, QtWidgets

from . import window_finder
from .calibration import CalibrationOverlay
from .hotkey import HotkeyBridge
from .icons import build_icon
from .tray import TrayController

WINDOW_STYLE = """
QWidget#root { background-color: #16171d; }
QLabel { color: #d8d8e0; }
QLabel#title { font-size: 19px; font-weight: 700; color: #ffffff; }
QLabel#subtitle { color: #8b8d9b; font-size: 12px; }
/* Qt stylesheets have no text-transform, so section text is uppercased
   in Python at the call site rather than here. */
QLabel#section {
    color: #6f7280; font-size: 10px; font-weight: 700; letter-spacing: 1.2px;
}
QLabel#statusOn { color: #4fd18c; font-size: 12px; font-weight: 600; }
QLabel#statusOff { color: #6f7280; font-size: 12px; }
QLabel#detail { color: #8b8d9b; font-size: 11px; }
QLabel#banner {
    background-color: #241f10;
    border: 1px solid #5c4e18;
    border-left: 3px solid #d9b23c;
    border-radius: 6px;
    padding: 10px 12px;
    color: #e0c675;
    font-size: 11px;
}
QLabel#footer { color: #5e6069; font-size: 10px; }
QPushButton#toggleOff {
    background-color: #2a2c36; color: #e8e8f0; border: 1px solid #3a3d49;
    border-radius: 10px; padding: 17px; font-size: 15px; font-weight: 600;
}
QPushButton#toggleOff:hover { background-color: #333642; border-color: #4a4e5c; }
QPushButton#toggleOff:pressed { background-color: #26282f; }
QPushButton#toggleOn {
    background-color: #4fd18c; color: #0d2118; border: 1px solid #5fdb99;
    border-radius: 10px; padding: 17px; font-size: 15px; font-weight: 700;
}
QPushButton#toggleOn:hover { background-color: #5edb99; }
QPushButton#toggleOn:pressed { background-color: #45c07f; }
QPushButton#secondary {
    background-color: #1e2026; color: #c2c4ce;
    border: 1px solid #33363f; border-radius: 7px;
    padding: 9px 12px; font-size: 12px;
}
QPushButton#secondary:hover { background-color: #272a32; border-color: #444853; }
QPushButton#secondary:pressed { background-color: #1a1c21; }
QFrame#sep { background-color: #26282f; max-height: 1px; }
"""


class MainWindow(QtWidgets.QWidget):
    def __init__(self, config, overlay):
        super().__init__()
        self.config = config
        self.overlay = overlay
        self._calibration_window = None
        self._trigger_calibration_window = None

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
        layout.setContentsMargins(22, 22, 22, 18)
        layout.setSpacing(11)

        title = QtWidgets.QLabel("KovaaK's Practice Mode")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QtWidgets.QLabel("Hide your score, high score, and rank.")
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

        calib_label = QtWidgets.QLabel("SCORE REGIONS")
        calib_label.setObjectName("section")
        layout.addWidget(calib_label)

        self.regions_label = QtWidgets.QLabel()
        self.regions_label.setObjectName("detail")
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

        sep1b = QtWidgets.QFrame()
        sep1b.setObjectName("sep")
        layout.addWidget(sep1b)

        trigger_label = QtWidgets.QLabel("BUTTON ZONES  ·  PLAY / NEXT / REPLAY")
        trigger_label.setObjectName("section")
        trigger_label.setWordWrap(True)
        layout.addWidget(trigger_label)

        self.trigger_regions_label = QtWidgets.QLabel()
        self.trigger_regions_label.setObjectName("detail")
        self.trigger_regions_label.setWordWrap(True)
        layout.addWidget(self.trigger_regions_label)

        trigger_row = QtWidgets.QHBoxLayout()
        self.calibrate_trigger_button = QtWidgets.QPushButton("Calibrate Button Zones...")
        self.calibrate_trigger_button.setObjectName("secondary")
        self.calibrate_trigger_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.calibrate_trigger_button.clicked.connect(self.start_trigger_calibration)
        trigger_row.addWidget(self.calibrate_trigger_button)

        self.clear_trigger_button = QtWidgets.QPushButton("Clear")
        self.clear_trigger_button.setObjectName("secondary")
        self.clear_trigger_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.clear_trigger_button.clicked.connect(self._on_clear_trigger_regions)
        trigger_row.addWidget(self.clear_trigger_button)
        layout.addLayout(trigger_row)

        sep2 = QtWidgets.QFrame()
        sep2.setObjectName("sep")
        layout.addWidget(sep2)

        banner = QtWidgets.QLabel(
            "KovaaK's must be set to Windowed Fullscreen (NOT Fullscreen - working on this), "
            "or Windows will hide the cover boxes. In KovaaK's: Settings → Video → Display Mode."
        )
        banner.setObjectName("banner")
        banner.setWordWrap(True)
        layout.addWidget(banner)

        footer = QtWidgets.QLabel(
            f"Hotkey: {self.config.hotkey}  •  Closing this window does NOT fully close the app. "
            "Right click the icon in your system tray (bottom right up arrow) to fully exit session."
        )
        footer.setObjectName("footer")
        footer.setWordWrap(True)
        layout.addWidget(footer)

    def _refresh_status(self):
        hwnd = window_finder.find_kovaaks_window()
        self.status_label.setText(
            "● KovaaK's detected" if hwnd else "○ KovaaK's not running"
        )
        self.status_label.setObjectName("statusOn" if hwnd else "statusOff")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

        enabled = self.config.practice_mode_enabled
        self.toggle_button.setObjectName("toggleOn" if enabled else "toggleOff")
        self.toggle_button.setText(
            "You're absolutely LOCKED (scores hidden)" if enabled else "Turn Practice Mode ON"
        )
        # Re-polish so the new objectName's stylesheet rule takes effect.
        self.toggle_button.style().unpolish(self.toggle_button)
        self.toggle_button.style().polish(self.toggle_button)

        count = len(self.config.regions)
        self.regions_label.setText(
            "No regions calibrated yet. Practice mode won't hide anything until you calibrate."
            if count == 0
            else f"{count} region{'s' if count != 1 else ''} calibrated."
        )

        trigger_count = len(self.config.trigger_regions)
        self.trigger_regions_label.setText(
            "Not calibrated. The score cover will only clear itself via the fallback "
            "timeout instead of clearing the moment you click to move on."
            if trigger_count == 0
            else f"{trigger_count} button zone{'s' if trigger_count != 1 else ''} calibrated."
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

    def _on_clear_trigger_regions(self):
        if not self.config.trigger_regions:
            return
        confirm = QtWidgets.QMessageBox.question(
            self, "Clear Button Zones", "Remove all calibrated button zones?"
        )
        if confirm == QtWidgets.QMessageBox.StandardButton.Yes:
            self.config.set_trigger_regions([])
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

    def start_trigger_calibration(self):
        hwnd = window_finder.find_kovaaks_window()
        if not hwnd:
            QtWidgets.QMessageBox.warning(
                self,
                "KovaaK's Practice Mode",
                "Couldn't find a running KovaaK's window. Launch the game first, then calibrate.",
            )
            return

        rect = window_finder.get_client_screen_rect(hwnd)
        calibration_window = CalibrationOverlay(
            rect,
            prompt=(
                "Drag boxes over Play/Next/Replay/scenario-list buttons - clicking one of "
                "these clears the score cover right away. Enter = save, Ctrl+Z = undo, Esc = cancel"
            ),
            accent_color=(90, 160, 240),
        )

        def on_finished(fractions):
            if fractions:
                self.config.set_trigger_regions(fractions)
            self._refresh_status()
            self._trigger_calibration_window = None

        calibration_window.finished.connect(on_finished)
        calibration_window.show()
        calibration_window.activateWindow()
        self._trigger_calibration_window = calibration_window  # keep alive while in use

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
