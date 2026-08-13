import os

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
    if not win32gui.GetWindowText(hwnd):
        return False
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        name = psutil.Process(pid).name()
    except Exception:
        return False
    # Matching on process name only. A title-substring fallback ("kovaak"
    # in the title) sounds harmless but isn't: it has already matched this
    # app's own window, a second copy of this app, and a code editor with
    # this project folder open, since all of those titles legitimately
    # contain "kovaak" too.
    return name in KOVAAKS_PROCESS_NAMES


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


def get_performances_dir(hwnd):
    """Return KovaaK's "performances" folder (where it writes a .perf file
    the instant each run completes), derived from the running exe's own
    path so it works regardless of which drive/Steam library it's
    installed to. None if it can't be determined."""
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        exe_path = psutil.Process(pid).exe()
    except Exception:
        return None

    # exe_path: .../FPSAimTrainer/Binaries/Win64/FPSAimTrainer-Win64-Shipping.exe
    win64_dir = os.path.dirname(exe_path)
    project_root = os.path.dirname(os.path.dirname(win64_dir))
    perf_dir = os.path.join(project_root, "performances")
    return perf_dir if os.path.isdir(perf_dir) else None
