"""One-off script: renders assets/icon.ico from the same design as the
in-app icon (src/icons.py), for use as the packaged .exe's file icon."""
import sys

from PyQt6 import QtGui, QtWidgets

sys.path.insert(0, "src")
from icons import build_icon  # noqa: E402

app = QtWidgets.QApplication(sys.argv)

sizes = [16, 24, 32, 48, 64, 128, 256]
icon = QtGui.QIcon()
for size in sizes:
    pixmap = build_icon(True, size).pixmap(size, size)
    icon.addPixmap(pixmap)

# QIcon has no direct multi-size .ico writer; save the largest pixmap and
# let Qt's ICO plugin pack it (it stores just the one size, which Windows
# still scales fine for taskbar/explorer use).
build_icon(True, 256).pixmap(256, 256).save("assets/icon.ico", "ICO")
print("wrote assets/icon.ico")
