"""Change Windows input styles without resetting Qt's layered rendering surface."""
import ctypes
from ctypes import wintypes

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000


def disable_pen_feedback(hwnd):
    """Suppress Windows Ink visuals for all tools on this canvas only."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    prop = user32.SetPropW
    prop.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.HANDLE]
    prop.restype = wintypes.BOOL
    if not prop(hwnd, "MicrosoftTabletPenServiceProperty", 0x00010019):
        raise ctypes.WinError(ctypes.get_last_error())
    feedback = user32.SetWindowFeedbackSetting
    feedback.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.DWORD,
                         ctypes.c_uint32, ctypes.c_void_p]
    feedback.restype = wintypes.BOOL
    disabled = wintypes.BOOL(False)
    for kind in (2, 3, 4, 5, 6):  # pen barrel, tap, double-tap, hold, right-tap
        if not feedback(hwnd, kind, 0, ctypes.sizeof(disabled), ctypes.byref(disabled)):
            raise ctypes.WinError(ctypes.get_last_error())


def set_click_through(hwnd, enabled):
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    get_style = user32.GetWindowLongW
    get_style.argtypes = [wintypes.HWND, ctypes.c_int]
    get_style.restype = wintypes.LONG
    set_style = user32.SetWindowLongW
    set_style.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
    set_style.restype = wintypes.LONG
    ctypes.set_last_error(0)
    old = get_style(hwnd, GWL_EXSTYLE)
    if not old and ctypes.get_last_error():
        raise ctypes.WinError(ctypes.get_last_error())
    mask = WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
    new = old | mask if enabled else old & ~mask
    if new == old:
        return
    ctypes.set_last_error(0)
    previous = set_style(hwnd, GWL_EXSTYLE, new)
    if not previous and ctypes.get_last_error():
        raise ctypes.WinError(ctypes.get_last_error())
    # Preserve WS_EX_LAYERED and its per-pixel alpha backing store. In
    # particular, do not call SetLayeredWindowAttributes or change Qt flags.
