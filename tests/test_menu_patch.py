import ctypes
import tempfile
import unittest
from unittest.mock import Mock, patch
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QToolButton
from test_core import APP
from screenpen.app import Toolbar
from screenpen.canvas import Canvas
from screenpen.panels import SettingsPanel
from screenpen import windows_input

class MenuPatchTests(unittest.TestCase):
    def test_settings_row_far_right_opens_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            canvas = Canvas(windowed=True)
            toolbar = Toolbar(canvas, QSettings(directory+'/settings.ini', QSettings.Format.IniFormat))
            toolbar.show()
            toolbar.open_menu(toolbar.more_menu, toolbar.copy_button)
            APP.processEvents()
            button = next(b for b in toolbar.more_menu.findChildren(QToolButton)
                          if b.defaultAction() and b.defaultAction().text() == 'Settings…')
            self.assertGreaterEqual(button.width(), toolbar.more_menu.scroll.viewport().width()-2)
            QTest.mouseClick(button, Qt.MouseButton.LeftButton,
                             pos=QPoint(button.width()-5, button.height()//2))
            self.assertIsInstance(toolbar.side_panel, SettingsPanel)
            toolbar.hide(); canvas.hide()
            toolbar.deleteLater(); canvas.deleteLater()

    def test_shape_menu_border_is_opaque_and_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            canvas = Canvas(windowed=True)
            toolbar = Toolbar(canvas, QSettings(directory+'/settings.ini', QSettings.Format.IniFormat))
            toolbar.show()
            toolbar.open_menu(toolbar.shape_menu, toolbar.shape_button)
            APP.processEvents()
            image = toolbar.shape_menu.grab().toImage()
            # The entire top border is the solid panel border, not transparent garbage.
            for x in range(2, image.width()-2):
                color = image.pixelColor(x, 0)
                self.assertEqual(color.alpha(), 255)
                self.assertGreater(color.red(), 150)
            toolbar.hide(); canvas.hide()
            toolbar.deleteLater(); canvas.deleteLater()

    def test_pen_feedback_disabled_for_canvas_without_global_settings(self):
        api = Mock()
        api.SetPropW.return_value = True
        seen = []
        def feedback(hwnd, kind, flags, size, data):
            seen.append((hwnd, kind, flags, ctypes.cast(data, ctypes.POINTER(windows_input.wintypes.BOOL)).contents.value))
            return True
        api.SetWindowFeedbackSetting.side_effect = feedback
        with patch.object(windows_input.ctypes, 'WinDLL', return_value=api, create=True):
            windows_input.disable_pen_feedback(123)
        api.SetPropW.assert_called_once_with(123, 'MicrosoftTabletPenServiceProperty', 0x10019)
        self.assertEqual(seen, [(123, kind, 0, 0) for kind in (2, 3, 4, 5, 6)])
