from PyQt6 import QtCore, QtGui, QtWidgets

from .icons import build_icon


class TrayController(QtCore.QObject):
    def __init__(self, config, on_calibrate, on_show_window):
        super().__init__()
        self.config = config

        self.tray = QtWidgets.QSystemTrayIcon()
        self.tray.setIcon(build_icon(config.practice_mode_enabled))
        self.tray.setToolTip("KovaaK's Practice Mode")

        self.menu = QtWidgets.QMenu()

        show_action = QtGui.QAction("Open Window", self.menu)
        show_action.triggered.connect(on_show_window)
        self.menu.addAction(show_action)

        self.toggle_action = QtGui.QAction("Practice Mode", self.menu, checkable=True)
        self.toggle_action.setChecked(config.practice_mode_enabled)
        self.toggle_action.toggled.connect(self.set_enabled)
        self.menu.addAction(self.toggle_action)

        calibrate_action = QtGui.QAction("Calibrate Score Regions...", self.menu)
        calibrate_action.triggered.connect(on_calibrate)
        self.menu.addAction(calibrate_action)

        self.menu.addSeparator()
        quit_action = QtGui.QAction("Quit", self.menu)
        quit_action.triggered.connect(QtWidgets.QApplication.quit)
        self.menu.addAction(quit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_activated)
        self.tray.show()

    def _on_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            self.set_enabled(not self.config.practice_mode_enabled)

    def set_enabled(self, value):
        self.config.practice_mode_enabled = value

        self.toggle_action.blockSignals(True)
        self.toggle_action.setChecked(value)
        self.toggle_action.blockSignals(False)

        self.tray.setIcon(build_icon(value))
        self.tray.showMessage(
            "KovaaK's Practice Mode",
            "Practice Mode ON — scores hidden" if value else "Practice Mode OFF — scores visible",
            QtWidgets.QSystemTrayIcon.MessageIcon.Information,
            1500,
        )
