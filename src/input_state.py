import ctypes


class _CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("hCursor", ctypes.c_void_p),
        ("ptScreenPos_x", ctypes.c_long),
        ("ptScreenPos_y", ctypes.c_long),
    ]


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


_user32 = ctypes.windll.user32
_CURSOR_SHOWING = 0x00000001
_VK_LBUTTON = 0x01


def _is_cursor_hidden():
    info = _CURSORINFO()
    info.cbSize = ctypes.sizeof(_CURSORINFO)
    _user32.GetCursorInfo(ctypes.byref(info))
    return not bool(info.flags & _CURSOR_SHOWING)


def _get_clip_rect():
    r = _RECT()
    if not _user32.GetClipCursor(ctypes.byref(r)):
        return None
    return (r.left, r.top, r.right, r.bottom)


class ClickTracker:
    """Detects a fresh left-click (a button-down transition, not just "is it
    currently held") and where it happened. Polling-based like everything
    else here - a click shorter than the poll interval could in principle be
    missed, but human clicks comfortably exceed that."""

    def __init__(self):
        self._was_down = False

    def poll(self):
        """Returns the (x, y) screen position of a just-started left click,
        or None if the button isn't newly down since the last poll()."""
        down = bool(_user32.GetAsyncKeyState(_VK_LBUTTON) & 0x8000)
        pos = None
        if down and not self._was_down:
            pt = _POINT()
            _user32.GetCursorPos(ctypes.byref(pt))
            pos = (pt.x, pt.y)
        self._was_down = down
        return pos


def is_actively_aiming(game_rect, tolerance=5):
    """True if the OS cursor is hidden and confined to (roughly) the given
    (x, y, width, height) game window rect. Games implementing raw-mouselook
    aiming hide the cursor and ClipCursor() it to their own window; in
    menus/results screens the cursor is visible and free to roam the full
    desktop. This distinguishes "actively aiming mid-run" from "looking at
    a menu or results screen" without reading game memory or screen pixels.
    """
    if not _is_cursor_hidden():
        return False

    clip = _get_clip_rect()
    if clip is None:
        return False

    gx, gy, gw, gh = game_rect
    clip_w = clip[2] - clip[0]
    clip_h = clip[3] - clip[1]
    return (
        abs(clip[0] - gx) <= tolerance
        and abs(clip[1] - gy) <= tolerance
        and abs(clip_w - gw) <= tolerance
        and abs(clip_h - gh) <= tolerance
    )
