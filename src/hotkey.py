import keyboard
from PyQt6 import QtCore


class HotkeyBridge(QtCore.QObject):
    """Bridges a global OS hotkey (via the `keyboard` library, which runs its
    own listener thread) into a Qt signal that's safe to connect to on the
    main thread."""

    triggered = QtCore.pyqtSignal()

    def __init__(self, hotkey: str):
        super().__init__()
        self.hotkey = hotkey
        self._handle = None

    def start(self):
        self._handle = keyboard.add_hotkey(self.hotkey, self.triggered.emit)

    def stop(self):
        if self._handle is not None:
            keyboard.remove_hotkey(self._handle)
            self._handle = None
