import sys

from PyQt6 import QtWidgets

from src.config import ConfigManager
from src.main_window import MainWindow
from src.overlay import OverlayWindow


def main():
    # Qt6's Windows platform plugin already sets per-monitor-v2 DPI
    # awareness on its own; calling SetProcessDpiAwareness ourselves here
    # races it and Windows rejects the second call.
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
        QtWidgets.QMessageBox.critical(None, "KovaaK's Practice Mode", "No system tray available.")
        sys.exit(1)

    config = ConfigManager()
    overlay = OverlayWindow(config)

    window = MainWindow(config, overlay)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
