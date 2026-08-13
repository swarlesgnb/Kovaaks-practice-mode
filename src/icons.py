from PyQt6 import QtCore, QtGui


def build_icon(active: bool, size: int = 64) -> QtGui.QIcon:
    """Circle-with-'P' icon, used for both the tray icon and the app/window
    icon. Green when Practice Mode is on, grey when off."""
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

    margin = max(2, size // 16)
    color = QtGui.QColor(80, 220, 140) if active else QtGui.QColor(140, 140, 150)
    painter.setBrush(color)
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)

    painter.setPen(QtGui.QColor(20, 20, 20))
    font = painter.font()
    font.setBold(True)
    font.setPointSize(int(size * 0.44))
    painter.setFont(font)
    painter.drawText(pixmap.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, "P")
    painter.end()

    return QtGui.QIcon(pixmap)
