import win32gui
import win32process
import psutil

KOVAAKS_PROCESS_NAMES = {
    "FPSAimTrainer-Win64-Shipping.exe",
    "FPSAimTrainer.exe",
}


def _window_matches(hwnd):
    if not win32gui.IsWindowVisible(hwnd):
        return False
    title = win32gui.GetWindowText(hwnd)
    if not title:
        return False
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        name = proc.name()
    except Exception:
        return False
    return name in KOVAAKS_PROCESS_NAMES or "kovaak" in title.lower()


def find_kovaaks_window():
    """Return the hwnd of the running KovaaK's window, or None if not found."""
    result = []

    def _enum(hwnd, _):
        if _window_matches(hwnd):
            result.append(hwnd)

    win32gui.EnumWindows(_enum, None)
    return result[0] if result else None


def get_client_screen_rect(hwnd):
    """Return (x, y, width, height) of the window's client area in screen coords."""
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    width, height = right - left, bottom - top
    origin_x, origin_y = win32gui.ClientToScreen(hwnd, (0, 0))
    return origin_x, origin_y, width, height
