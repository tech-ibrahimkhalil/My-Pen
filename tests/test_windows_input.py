import unittest
from unittest.mock import Mock, patch
from screenpen import windows_input
from test_core import APP
from screenpen.canvas import Canvas

class WindowsInputTests(unittest.TestCase):
    def test_style_toggles_preserve_layered_surface_and_other_styles(self):
        original = 0x80000 | 0x80 | 0x8  # layered, toolwindow, topmost
        state = [original]
        api = Mock()
        api.GetWindowLongW.side_effect = lambda *_: state[0]
        def write(hwnd, index, style):
            previous = state[0]
            state[0] = style
            return previous
        api.SetWindowLongW.side_effect = write
        with patch.object(windows_input.ctypes, 'WinDLL', return_value=api, create=True), \
             patch.object(windows_input.ctypes, 'set_last_error', create=True), \
             patch.object(windows_input.ctypes, 'get_last_error', return_value=0, create=True):
            for _ in range(30):
                windows_input.set_click_through(123, True)
                self.assertEqual(state[0], original | 0x08000020)
                windows_input.set_click_through(123, False)
                self.assertEqual(state[0], original)
            count = api.SetWindowLongW.call_count
            windows_input.set_click_through(123, False)
            self.assertEqual(api.SetWindowLongW.call_count, count)
        self.assertFalse(api.SetLayeredWindowAttributes.called)

    def test_windows_switch_avoids_qt_flags_and_keeps_window_and_ink(self):
        canvas = Canvas()
        canvas.show()
        original = canvas.winId()
        with patch('screenpen.canvas.sys.platform', 'win32'), \
             patch('screenpen.windows_input.set_click_through') as native, \
             patch.object(canvas, 'apply_qt_input_flags') as qt:
            for _ in range(30):
                canvas.set_ghost(True)
                canvas.set_ghost(False)
                self.assertTrue(canvas.isVisible())
                self.assertEqual(original, canvas.winId())
            self.assertEqual(native.call_count, 60)
            qt.assert_not_called()
        canvas.hide()
        canvas.deleteLater()

    def test_native_failure_uses_qt_fallback(self):
        canvas = Canvas()
        canvas.winId()
        with patch('screenpen.canvas.sys.platform', 'win32'), \
             patch('screenpen.windows_input.set_click_through', side_effect=OSError('test')), \
             patch.object(canvas, 'apply_qt_input_flags') as qt, \
             self.assertLogs('screenpen.canvas', level='ERROR'):
            canvas.apply_input_mode()
            qt.assert_called_once()
        canvas.deleteLater()
