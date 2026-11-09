"""Native message regression; hardware feedback still needs Windows testing."""
import ctypes
from ctypes import wintypes
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from unittest.mock import patch
from PySide6.QtCore import QByteArray
from PySide6.QtWidgets import QApplication
from screenpen.canvas import Canvas

APP = QApplication.instance() or QApplication([])

class PenFeedbackTests(unittest.TestCase):
    def test_windows_pen_gesture_query_disables_feedback(self):
        for windowed in (True, False):
            canvas = Canvas(windowed=windowed)
            msg = wintypes.MSG()
            msg.message = 0x02CC
            with patch('screenpen.canvas.sys.platform', 'win32'):
                handled, flags = canvas.nativeEvent(
                    QByteArray(b'windows_generic_MSG'), ctypes.addressof(msg))
            self.assertTrue(handled)
            for flag in (0x1, 0x8, 0x10, 0x10000):
                self.assertTrue(flags & flag)
            canvas.deleteLater()

    def test_other_platforms_do_not_dereference_windows_message(self):
        canvas = Canvas(windowed=True)
        for platform in ('linux', 'darwin'):
            with patch('screenpen.canvas.sys.platform', platform):
                handled, _ = canvas.nativeEvent(b'windows_generic_MSG', 0)
            self.assertFalse(handled)
        canvas.deleteLater()

    def test_unrelated_windows_messages_are_not_swallowed(self):
        canvas = Canvas(windowed=True)
        msg = wintypes.MSG()
        msg.message = 0x0200  # WM_MOUSEMOVE
        with patch('screenpen.canvas.sys.platform', 'win32'):
            handled, _ = canvas.nativeEvent(b'windows_generic_MSG', ctypes.addressof(msg))
        self.assertFalse(handled)
        canvas.deleteLater()
