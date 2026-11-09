"""Run with: python -m unittest discover -s tests -v"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import subprocess
import sys
from unittest.mock import Mock, patch
import unittest
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRect, QSettings, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QKeySequence, QPixmap, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit, QMessageBox, QToolButton

from screenpen.canvas import Canvas
from screenpen.drawing import Document, Mark
from screenpen.app import Toolbar
from screenpen.dialogs import run_dialog
from screenpen.capture import CaptureSelector, crop_pixels
from screenpen.panels import ColorPanel, SettingsPanel

APP = QApplication.instance() or QApplication([])


def line(y=20):
    return Mark("line", "#ff0000", 4, [(10, y, 1), (100, y, 1)])


class DrawingTests(unittest.TestCase):
    def setUp(self):
        self.canvas = Canvas(windowed=True)
        self.canvas.resize(300, 200)

    def tearDown(self):
        self.canvas.hide()
        self.canvas.deleteLater()

    def test_mouse_drag_creates_stroke(self):
        self.canvas.show()
        QTest.mousePress(self.canvas, Qt.MouseButton.LeftButton, pos=QPoint(20, 30))
        QTest.mouseMove(self.canvas, QPoint(120, 30))
        QTest.mouseRelease(self.canvas, Qt.MouseButton.LeftButton, pos=QPoint(150, 30))
        self.assertEqual(len(self.canvas.document.marks), 1)
        self.assertEqual(self.canvas.document.marks[0].points[-1][:2], (150, 30))

    def test_undo_redo_and_new_branch(self):
        doc = Document()
        doc.add(line())
        doc.add(line(50))
        doc.undo()
        self.assertEqual(len(doc.marks), 1)
        doc.redo()
        self.assertEqual(len(doc.marks), 2)
        doc.undo()
        doc.add(line(80))
        doc.redo()
        self.assertEqual([m.points[0][1] for m in doc.marks], [20, 80])

    def test_swept_eraser_crosses_thin_stroke(self):
        doc = Document()
        doc.add(line())
        self.assertTrue(doc.erase(QPointF(50, 0), QPointF(50, 80), 2))
        self.assertEqual(doc.marks, [])
        doc.undo()
        self.assertEqual(len(doc.marks), 1)

    def test_empty_erase_preserves_redo(self):
        doc = Document()
        doc.add(line())
        doc.undo()
        self.assertFalse(doc.erase(QPointF(200, 100), QPointF(200, 150), 5))
        doc.redo()
        self.assertEqual(len(doc.marks), 1)

    def test_eraser_gesture_is_one_undo(self):
        self.canvas.document.add(line(20))
        self.canvas.document.add(line(80))
        self.canvas.tool = "eraser"
        self.canvas.begin(QPointF(50, 20))
        self.canvas.move_input(QPointF(50, 80))
        self.canvas.end()
        self.assertEqual(len(self.canvas.document.marks), 0)
        self.canvas.document.undo()
        self.assertEqual(len(self.canvas.document.marks), 2)

    def test_clear_is_undoable(self):
        self.canvas.document.add(line())
        self.canvas.document.clear()
        self.canvas.document.undo()
        self.assertEqual(len(self.canvas.document.marks), 1)

    def test_ghost_blocks_drawing_without_losing_marks(self):
        self.canvas.document.add(line())
        self.canvas.set_ghost(True)
        self.canvas.begin(QPointF(150, 150))
        self.canvas.end()
        self.assertEqual(len(self.canvas.document.marks), 1)
        self.canvas.set_ghost(False)
        self.canvas.begin(QPointF(150, 150))
        self.canvas.end()
        self.assertEqual(len(self.canvas.document.marks), 2)

    def test_shift_creates_square(self):
        self.canvas.tool = "rectangle"
        self.canvas.begin(QPointF(10, 10))
        self.canvas.move_input(QPointF(80, 40), modifiers=Qt.KeyboardModifier.ShiftModifier)
        self.canvas.end()
        self.assertEqual(self.canvas.document.marks[0].points[-1][:2], (80, 80))

    def test_export_background_and_actual_pixels(self):
        self.canvas.document.add(line())
        self.canvas.board = "transparent"
        image = self.canvas.export_image()
        ratio = image.devicePixelRatio()
        self.assertEqual(image.pixelColor(round(200 * ratio), round(150 * ratio)).alpha(), 0)
        self.assertGreater(image.pixelColor(round(50 * ratio), round(20 * ratio)).red(), 200)
        self.canvas.board = "black"
        self.assertEqual(self.canvas.export_image().pixelColor(200, 150).name(), "#000000")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(image.save(str(Path(tmp) / "test.png")))

    def test_highlighter_does_not_darken_self_overlap(self):
        self.canvas.board = "transparent"
        self.canvas.document.add(Mark("highlighter", "#ffff00", 20,
                                      [(20, 60, 1), (120, 60, 1), (20, 60, 1)]))
        image = self.canvas.export_image()
        ratio = image.devicePixelRatio()
        alpha = image.pixelColor(round(60 * ratio), round(60 * ratio)).alpha()
        self.assertTrue(70 <= alpha <= 85, alpha)

    def test_pressure_changes_stroke_thickness(self):
        self.canvas.board = "transparent"
        self.canvas.document.add(Mark("pen", "#ff0000", 20, [(50, 50, 0.2)]))
        self.canvas.document.add(Mark("pen", "#ff0000", 20, [(100, 50, 1)]))
        image = self.canvas.export_image()
        ratio = image.devicePixelRatio()
        self.assertEqual(image.pixelColor(round(50 * ratio), round(56 * ratio)).alpha(), 0)
        self.assertGreater(image.pixelColor(round(100 * ratio), round(56 * ratio)).alpha(), 200)

    def test_all_shapes_and_text_render(self):
        for kind in ["line", "arrow", "rectangle", "ellipse", "text"]:
            mark = Mark(kind, "#ff0000", 4, [(20, 50, 1), (100, 100, 1)], text="UE test")
            self.canvas.document.add(mark)
            self.assertFalse(mark.outline().isEmpty())
        self.assertFalse(self.canvas.export_image().isNull())

    def test_toolbar_return_from_ghost_and_tool_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = QSettings(str(Path(tmp) / "test.ini"), QSettings.Format.IniFormat)
            toolbar = Toolbar(self.canvas, settings)
            toolbar.ghost_button.setChecked(True)
            self.assertTrue(self.canvas.ghost)
            toolbar.select_tool("arrow")
            self.assertFalse(self.canvas.ghost)
            self.assertEqual(self.canvas.tool, "arrow")
            self.assertFalse(toolbar.ghost_button.isChecked())
            toolbar.deleteLater()

    def test_windowed_application_starts_and_exits(self):
        self.check_smoke("--windowed")

    def test_overlay_application_starts_and_exits(self):
        self.check_smoke("--overlay")

    def check_smoke(self, mode):
        result = subprocess.run([sys.executable, "main.py", mode, "--smoke-test"],
                                cwd=Path(__file__).resolve().parents[1],
                                env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


class CompactToolbarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.canvas = Canvas(windowed=True)
        self.canvas.resize(300, 200)
        settings = QSettings(str(Path(self.tmp.name) / "toolbar.ini"), QSettings.Format.IniFormat)
        self.toolbar = Toolbar(self.canvas, settings)

    def tearDown(self):
        self.toolbar.close_sidebar()
        self.toolbar.hide()
        self.toolbar.deleteLater()
        self.canvas.deleteLater()
        QApplication.clipboard().clear()
        self.tmp.cleanup()

    def test_eye_hides_without_deleting_and_tool_restores_visibility(self):
        self.canvas.document.add(line())
        self.toolbar.eye_button.setChecked(False)
        self.assertFalse(self.canvas.ink_visible)
        self.assertEqual(len(self.canvas.document.marks), 1)
        self.toolbar.tool_actions["highlighter"].trigger()
        self.assertTrue(self.canvas.ink_visible)
        self.assertEqual(self.canvas.tool, "highlighter")

    def test_cursor_button_and_each_dropdown_tool(self):
        for tool in ["pen", "highlighter", "text", "line", "arrow", "rectangle", "ellipse"]:
            self.toolbar.ghost_button.click()
            self.assertTrue(self.canvas.ghost)
            self.toolbar.tool_actions[tool].trigger()
            self.assertEqual(self.canvas.tool, tool)
            self.assertFalse(self.canvas.ghost)
        self.toolbar.eraser_button.click()
        self.assertEqual(self.canvas.tool, "eraser")

    def test_color_palette_expansion_and_quick_colors(self):
        self.toolbar.palette_mode.setCurrentIndex(1)
        self.assertTrue(all(not button.isHidden() for button in self.toolbar.swatches))
        self.toolbar.palette_mode.setCurrentIndex(0)
        self.assertTrue(all(button.isHidden() for button in self.toolbar.swatches[16:]))
        self.toolbar.quick_colors[0].click()
        self.assertEqual(self.canvas.color, "#00c8ed")

    def test_clipboard_contains_rendered_canvas(self):
        self.canvas.document.add(line())
        self.toolbar.copy_canvas()
        image = QApplication.clipboard().image()
        self.assertFalse(image.isNull())
        ratio = image.devicePixelRatio()
        self.assertGreater(image.pixelColor(round(50 * ratio), round(20 * ratio)).red(), 200)

    def test_board_menu_preserves_annotations(self):
        self.canvas.document.add(line())
        self.toolbar.board_actions[2].trigger()
        self.assertEqual(self.canvas.board, "black")
        self.toolbar.board_actions[0].trigger()
        self.assertEqual(self.canvas.board, "transparent")
        self.assertEqual(len(self.canvas.document.marks), 1)

    def test_flyout_buttons_choose_tools_and_sizes(self):
        self.toolbar.ink_menu.icon_buttons[1].click()
        self.assertEqual(self.canvas.tool, "highlighter")
        self.toolbar.shape_menu.icon_buttons[3].click()
        self.assertEqual(self.canvas.tool, "arrow")
        self.toolbar.width_menu.icon_buttons[3].click()
        self.assertEqual(self.canvas.stroke_width, 14)

    def test_fading_ink_expires_without_resurrecting_through_history(self):
        self.toolbar.fade_menu.icon_buttons[2].click()
        self.assertEqual(self.canvas.fade_seconds, 3)
        self.canvas.begin(QPointF(10, 10))
        self.canvas.move_input(QPointF(100, 10))
        self.canvas.end()
        mark = self.canvas.document.marks[-1]
        self.assertEqual(mark.opacity(mark.created_at + 1), 1)
        self.assertAlmostEqual(mark.opacity(mark.created_at + 2.5), 0.5)
        self.assertEqual(mark.opacity(mark.created_at + 3.1), 0)
        self.canvas.document.add(line(70))
        self.canvas.document.expire(mark.created_at + 4)
        self.canvas.document.undo()
        self.assertNotIn(mark, self.canvas.document.marks)
        self.canvas.document.redo()
        self.assertNotIn(mark, self.canvas.document.marks)

    def test_fade_preset_does_not_change_existing_permanent_ink(self):
        self.canvas.document.add(line())
        self.toolbar.choose_fade(1)
        self.assertEqual(self.canvas.document.marks[0].fade_after, 0)

    def test_highlighted_cursor_keeps_ghost_and_can_return_to_drawing(self):
        self.toolbar.cursor_menu.icon_buttons[1].click()
        self.assertTrue(self.canvas.highlight_cursor)
        self.assertTrue(self.canvas.ghost)
        self.toolbar.select_tool("pen")
        self.assertFalse(self.canvas.ghost)
        self.assertTrue(self.canvas.highlight_cursor)
        self.toolbar.cursor_menu.icon_buttons[0].click()
        self.assertFalse(self.canvas.highlight_cursor)

    def test_exit_quits_without_confirmation_even_with_drawings(self):
        self.canvas.document.add(line())
        self.toolbar.message = Mock()
        with patch.object(APP, "quit") as quit_app:
            self.assertTrue(self.toolbar.request_quit())
            quit_app.assert_called_once()
        self.toolbar.message.assert_not_called()

    def test_glass_controls_and_export_alpha(self):
        self.toolbar.open_settings()
        panel = self.toolbar.settings_panel
        panel.toolbar_glass.setChecked(True)
        panel.toolbar_opacity.setValue(65)
        panel.background_glass.setChecked(True)
        panel.background_opacity.setValue(35)
        self.assertAlmostEqual(self.toolbar.windowOpacity(), .65, delta=.01)
        self.assertEqual(self.canvas.export_image().pixelColor(150, 150).alpha(), round(255*.35))
        self.assertTrue(self.toolbar.settings.value("toolbar_glass", type=bool))
        panel.background_glass.setChecked(False)
        self.assertEqual(self.canvas.export_image().pixelColor(150, 150).alpha(), 255)

    def test_tray_hide_restore_preserves_work_and_survives_repeated_hide(self):
        self.canvas.document.add(line())
        self.canvas.show()
        self.toolbar.show()
        self.toolbar.tray = Mock()
        self.toolbar.tray.isVisible.return_value = True
        self.toolbar.hide_to_tray()
        self.toolbar.hide_to_tray()
        self.assertFalse(self.toolbar.isVisible())
        self.assertFalse(self.canvas.isVisible())
        self.toolbar.restore_from_tray()
        self.assertTrue(self.toolbar.isVisible())
        self.assertTrue(self.canvas.isVisible())
        self.assertEqual(len(self.canvas.document.marks), 1)

    def test_tray_unavailable_keeps_reopen_control(self):
        self.toolbar.show()
        with patch("screenpen.app.QSystemTrayIcon.isSystemTrayAvailable", return_value=False):
            self.assertFalse(self.toolbar.init_tray())
        self.toolbar.hide_to_tray()
        self.assertTrue(self.toolbar.isVisible())
        self.assertTrue(self.toolbar.collapsed)

    def test_startup_prompt_decline_never_registers_and_is_not_repeated(self):
        self.toolbar.startup_manager = Mock()
        self.toolbar.offer_startup()
        self.toolbar.side_panel.decline()
        self.toolbar.startup_manager.set_enabled.assert_not_called()
        self.toolbar.offer_startup()
        self.assertIsNone(self.toolbar.side_panel)

    def test_startup_consent_registers_only_after_enable(self):
        self.toolbar.startup_manager = Mock()
        self.toolbar.offer_startup()
        self.toolbar.startup_manager.set_enabled.assert_not_called()
        self.toolbar.side_panel.enable()
        self.toolbar.startup_manager.set_enabled.assert_called_once_with(True)
        self.assertIsNone(self.toolbar.side_panel)

    def test_modal_yes_and_ghost_state_restore(self):
        self.canvas.set_ghost(True)
        self.canvas.show()

        def click_yes():
            dialog = QApplication.activeModalWidget()
            QTest.mouseClick(dialog.button(QMessageBox.StandardButton.Yes), Qt.MouseButton.LeftButton)

        QTimer.singleShot(20, click_yes)
        answer = self.toolbar.message("Test", "Continue?", question=True)
        self.assertEqual(answer, QMessageBox.StandardButton.Yes)
        self.assertTrue(self.canvas.isVisible())
        self.assertTrue(self.canvas.ghost)

    def test_modal_restores_hidden_canvas_as_hidden(self):
        dialog = QDialog(self.toolbar)
        self.canvas.hide()
        QTimer.singleShot(20, dialog.reject)
        self.assertEqual(run_dialog(dialog, self.canvas), QDialog.DialogCode.Rejected)
        self.assertFalse(self.canvas.isVisible())

    def test_text_is_inline_and_tool_hotkeys_do_not_intercept_typing(self):
        self.canvas.tool = "text"
        self.canvas.show()
        self.canvas.begin(QPointF(20, 60))
        editor = self.canvas.text_editor
        self.assertIs(editor.parentWidget(), self.canvas)
        self.assertFalse(editor.isWindow())
        self.assertTrue(all(not shortcut.isEnabled() for shortcut in self.toolbar.shortcuts))
        QTest.keyClicks(editor, "My Pen note")
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.assertTrue(self.canvas.isVisible())
        self.assertIsNone(self.canvas.text_editor)
        self.assertEqual(self.canvas.document.marks[-1].text, "My Pen note")
        self.assertTrue(all(shortcut.isEnabled() for shortcut in self.toolbar.shortcuts))

    def test_panel_internal_click_stays_open_and_outside_click_dismisses(self):
        self.canvas.resize(900, 600)
        self.canvas.show()
        self.toolbar.move(700, 30)
        self.toolbar.show()
        self.toolbar.open_settings()
        APP.processEvents()
        panel = self.toolbar.side_panel
        QTest.mouseClick(panel.highlight, Qt.MouseButton.LeftButton)
        self.assertIs(self.toolbar.side_panel, panel)
        QTest.mouseClick(self.canvas, Qt.MouseButton.LeftButton, pos=QPoint(40, 40))
        self.assertIsNone(self.toolbar.side_panel)

    def test_external_app_deactivation_dismisses_panel(self):
        self.toolbar.open_settings()
        self.toolbar.application_state_changed(Qt.ApplicationState.ApplicationInactive)
        self.assertIsNone(self.toolbar.side_panel)

    def test_main_icon_asset_is_loadable(self):
        from screenpen.icons import make_icon
        icon = make_icon("logo")
        self.assertFalse(icon.isNull())
        self.assertFalse(icon.pixmap(48, 48).isNull())

    def test_compact_dimensions_and_collapse_reopen_preserve_work(self):
        self.canvas.document.add(line())
        self.canvas.show()
        self.toolbar.show()
        APP.processEvents()
        self.assertEqual(self.toolbar.width(), 48)
        self.assertEqual(self.toolbar.strip.width(), 34)
        self.assertLess(self.toolbar.height(), 470)
        self.toolbar.close()
        APP.processEvents()
        self.assertTrue(self.toolbar.collapsed)
        self.assertFalse(self.canvas.isVisible())
        self.assertTrue(self.toolbar.reopen_button.isVisible())
        self.assertLess(self.toolbar.height(), 90)
        self.toolbar.reopen_button.click()
        APP.processEvents()
        self.assertFalse(self.toolbar.collapsed)
        self.assertTrue(self.canvas.isVisible())
        self.assertTrue(self.toolbar.strip.isVisible())
        self.assertEqual(len(self.canvas.document.marks), 1)

    def test_main_menu_offers_exit_instead_of_close_toolbar(self):
        labels = [action.text() for action in self.toolbar.more_menu.actions()]
        self.assertNotIn("Close toolbar", labels)
        action = next(action for action in self.toolbar.more_menu.actions() if action.text() == "Exit My Pen")
        with patch.object(APP, "quit") as quit_app:
            action.trigger()
            quit_app.assert_called_once()
        self.assertTrue(self.toolbar._quitting)

    def test_eye_collapses_and_closed_eye_restores_canvas(self):
        self.canvas.show()
        self.toolbar.show()
        self.toolbar.eye_button.click()
        self.assertTrue(self.toolbar.collapsed)
        self.assertFalse(self.toolbar.strip.isVisible())
        self.assertFalse(self.canvas.isVisible())
        self.toolbar.reopen_button.click()
        self.assertFalse(self.toolbar.collapsed)
        self.assertTrue(self.canvas.isVisible())
        self.assertTrue(self.canvas.ink_visible)

    def test_rgb_is_attached_and_updates_exact_hex(self):
        self.toolbar.move(500, 100)
        self.toolbar.show()
        self.toolbar.custom_color()
        panel = self.toolbar.side_panel
        self.assertIs(panel.window(), self.toolbar)
        self.assertLessEqual(panel.height(), self.toolbar.strip.height())
        panel.hex.setText("#1234ab")
        panel.apply_color()
        self.assertEqual(self.canvas.color, "#1234ab")
        self.assertIsNone(self.toolbar.side_panel)

    def test_custom_background_exports_color(self):
        self.toolbar.custom_background()
        panel = self.toolbar.side_panel
        panel.hex.setText("#ccffaa")
        panel.apply_color()
        self.assertEqual(self.canvas.board, "custom")
        image = self.canvas.export_image()
        self.assertEqual(image.pixelColor(150, 150).name(), "#ccffaa")
        self.toolbar.board_actions[0].trigger()
        self.assertEqual(self.canvas.board, "transparent")

    def test_custom_fading_time_persists_and_controls_new_marks(self):
        self.toolbar.open_settings()
        self.toolbar.settings_panel.timer_edit.setValue(17)
        self.assertEqual(self.canvas.fade_seconds, 17)
        self.assertEqual(self.toolbar.settings.value("fade_seconds", type=int), 17)
        self.toolbar.close_sidebar()
        self.canvas.begin(QPointF(20, 20))
        self.canvas.end()
        self.assertEqual(self.canvas.document.marks[-1].fade_after, 17)
        self.toolbar.choose_fade(0)
        self.toolbar.fade_button.click()
        self.assertEqual(self.canvas.fade_seconds, 17)

    def test_toolbar_excluded_from_canvas_input_and_native_mask(self):
        self.canvas.resize(800, 600)
        self.canvas.move(0, 0)
        self.canvas.show()
        self.toolbar.move(100, 60)
        self.toolbar.show()
        APP.processEvents()
        point = self.canvas.mapFromGlobal(self.toolbar.ink_button.mapToGlobal(QPoint(14, 14)))
        self.assertTrue(self.canvas.protected(QPointF(point)))
        self.assertFalse(self.canvas.mask().contains(point))
        self.canvas.begin(QPointF(point))
        self.assertIsNone(self.canvas.pending)
        self.canvas.begin(QPointF(400, 40))
        self.canvas.move_input(QPointF(point))
        self.assertIsNotNone(self.canvas.pending)
        self.assertEqual(self.canvas.pending.points[-1][:2], (point.x(), point.y()))
        count = len(self.canvas.document.marks)
        self.canvas.move_input(QPointF(450, 40))
        self.assertEqual(len(self.canvas.document.marks), count)
        self.canvas.end()
        self.assertEqual(len(self.canvas.document.marks), count + 1)
        self.toolbar.open_settings()
        point = self.canvas.mapFromGlobal(self.toolbar.side_panel.mapToGlobal(QPoint(20, 20)))
        self.assertTrue(self.canvas.protected(QPointF(point)))

    def test_selected_tool_cursors_and_shape_arrow_pointers(self):
        keys = []
        for tool in ("pen", "highlighter", "eraser"):
            self.toolbar.select_tool(tool)
            self.assertFalse(self.canvas.cursor().pixmap().isNull())
            keys.append(self.canvas.cursor().pixmap().cacheKey())
        self.assertEqual(len(set(keys)), 3)
        for tool in ("line", "arrow", "rectangle", "ellipse"):
            self.toolbar.select_tool(tool)
            self.assertEqual(self.canvas.cursor().shape(), Qt.CursorShape.ArrowCursor)

    def test_inline_text_escape_cancels_without_mark(self):
        self.canvas.tool = "text"
        self.canvas.begin(QPointF(20, 50))
        QTest.keyClicks(self.canvas.text_editor, "cancel me")
        QTest.keyClick(self.canvas.text_editor, Qt.Key.Key_Escape)
        self.assertIsNone(self.canvas.text_editor)
        self.assertEqual(self.canvas.document.marks, [])

    def test_pen_and_highlighter_use_exact_selected_size(self):
        for size in (2, 4, 8, 14, 24):
            self.toolbar.width_input.setValue(size)
            for tool in ("pen", "highlighter", "line"):
                self.toolbar.select_tool(tool)
                self.canvas.begin(QPointF(20, 50))
                self.canvas.move_input(QPointF(150, 50))
                self.canvas.end()
                self.assertEqual(self.canvas.document.marks[-1].width, size)
            self.assertIn(f"{size} px", self.toolbar.width_button.toolTip())

    def test_screenshot_restores_toolbar_and_ink_after_cancel(self):
        self.canvas.show()
        self.toolbar.show()
        self.canvas.document.add(line())
        screen = Mock()
        screen.geometry.return_value = QRect(0, 0, 300, 200)
        image = QImage(300, 200, QImage.Format.Format_RGB32)
        image.fill(QColor("#cccccc"))
        screen.grabWindow.return_value = QPixmap.fromImage(image)
        with patch("screenpen.app.QTimer.singleShot"), patch.object(self.canvas, "screen", return_value=screen):
            self.toolbar.screenshot()
            self.assertFalse(self.canvas.isVisible())
            self.assertFalse(self.toolbar.isVisible())
            self.toolbar.take_screenshot()
        self.assertIsNotNone(self.toolbar.capture_selector)
        self.toolbar.capture_selector.finish()
        self.assertFalse(self.toolbar._capture_active)
        self.assertTrue(self.toolbar.isVisible())
        self.assertTrue(self.canvas.isVisible())
        self.assertEqual(len(self.canvas.document.marks), 1)

    def test_side_color_bar_restores_drawing_mode_on_selection(self):
        self.canvas.show()
        self.toolbar.show()
        self.toolbar.open_palette()
        self.assertIsInstance(self.toolbar.side_panel, ColorPanel)
        self.assertEqual(self.toolbar.palette_panel.width(), 84)
        self.assertFalse(self.canvas.ghost)
        self.assertTrue(all(key.isEnabled() for key in self.toolbar.shortcuts))
        self.toolbar.swatches[1].click()
        self.assertEqual(self.canvas.color, "#00bf42")
        self.assertIsNone(self.toolbar.side_panel)
        self.assertFalse(self.canvas.ghost)
        self.assertTrue(all(key.isEnabled() for key in self.toolbar.shortcuts))

    def test_settings_panel_controls_save_preferences(self):
        self.toolbar.show()
        self.toolbar.open_settings()
        panel = self.toolbar.side_panel
        self.assertIsInstance(panel, SettingsPanel)
        panel.per_tool.setChecked(True)
        panel.wheel.setChecked(False)
        panel.width_edit.setValue(12)
        panel.font_edit.setValue(32)
        panel.entire.setChecked(True)
        panel.fixed.setChecked(True)
        self.assertTrue(self.toolbar.per_tool_size)
        self.assertFalse(self.canvas.wheel_adjusts_size)
        self.assertEqual(self.canvas.stroke_width, 12)
        self.assertEqual(self.canvas.font_size, 32)
        self.assertTrue(self.toolbar.screenshot_entire)
        self.assertFalse(self.toolbar.screenshot_ask)
        self.assertTrue(self.toolbar.settings.value("per_tool_size", type=bool))
        self.assertEqual(self.toolbar.settings.value("font_size", type=int), 32)
        self.toolbar.close_sidebar()
        self.assertFalse(self.canvas.ghost)

    def test_each_tool_can_remember_a_different_width(self):
        self.toolbar.set_per_tool_size(True)
        self.toolbar.width_input.setValue(18)
        self.toolbar.select_tool("line")
        self.toolbar.width_input.setValue(5)
        self.toolbar.select_tool("pen")
        self.assertEqual(self.canvas.stroke_width, 18)
        self.toolbar.select_tool("line")
        self.assertEqual(self.canvas.stroke_width, 5)

    def test_wheel_size_setting_and_ghost_passthrough(self):
        def wheel():
            return QWheelEvent(QPointF(30, 30), QPointF(30, 30), QPoint(), QPoint(0,120),
                               Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                               Qt.ScrollPhase.ScrollUpdate, False)
        self.canvas.wheelEvent(wheel())
        self.assertEqual(self.canvas.stroke_width, 5)
        self.toolbar.set_wheel_size(False)
        self.canvas.wheelEvent(wheel())
        self.assertEqual(self.canvas.stroke_width, 5)
        self.toolbar.set_wheel_size(True)
        self.canvas.set_ghost(True)
        self.canvas.wheelEvent(wheel())
        self.assertEqual(self.canvas.stroke_width, 5)

    def test_custom_hotkey_conflicts_disable_and_reset(self):
        self.assertFalse(self.toolbar.update_shortcut(0, self.toolbar.shortcuts[1].key()))
        self.assertTrue(self.toolbar.update_shortcut(0, QKeySequence("Ctrl+Alt+P")))
        self.assertEqual(self.toolbar.shortcuts[0].key(), QKeySequence("Ctrl+Alt+P"))
        self.toolbar.set_hotkeys_disabled(True)
        self.assertTrue(all(not key.isEnabled() for key in self.toolbar.shortcuts))
        self.toolbar.reset_hotkeys()
        self.assertEqual(self.toolbar.shortcuts[0].key(), QKeySequence("P"))
        self.toolbar.set_hotkeys_disabled(False)
        self.assertTrue(all(key.isEnabled() for key in self.toolbar.shortcuts))

    def test_edited_quick_color_is_used_by_toolbar(self):
        self.toolbar.set_quick_color(0, "#123456")
        self.toolbar.quick_colors[0].click()
        self.assertEqual(self.canvas.color, "#123456")
        self.assertEqual(self.toolbar.settings.value("quick_colors/0"), "#123456")

    def test_sidebar_switch_and_collapse_leave_no_panel_open(self):
        self.toolbar.show()
        self.toolbar.open_palette()
        self.toolbar.open_settings()
        self.assertFalse(self.toolbar.palette_panel.isVisible())
        self.assertIsInstance(self.toolbar.side_panel, SettingsPanel)
        self.toolbar.collapse_toolbar()
        self.assertIsNone(self.toolbar.side_panel)
        self.assertTrue(self.toolbar.collapsed)

    def test_modal_temporarily_hides_and_restores_sidebar(self):
        self.canvas.show()
        self.toolbar.show()
        self.toolbar.open_settings()
        panel = self.toolbar.side_panel
        observed = []
        def dismiss():
            observed.append(not panel.isVisible() and not self.canvas.isVisible())
            QApplication.activeModalWidget().accept()
        QTimer.singleShot(20, dismiss)
        self.toolbar.message("Test", "Settings modal")
        self.assertEqual(observed, [True])
        self.assertTrue(panel.isVisible())
        self.assertTrue(self.canvas.isVisible())

    def test_all_bundled_lucide_icons_render_pixels(self):
        from screenpen.icons import ICON_NAMES, make_icon
        for name in ICON_NAMES:
            image = make_icon(name).pixmap(32,32).toImage()
            self.assertFalse(image.isNull(), name)
            self.assertTrue(any(image.pixelColor(x,y).alpha() for x in range(image.width())
                                for y in range(image.height())), name)

    def test_reset_preferences_keeps_drawings_and_reopens_settings(self):
        self.canvas.document.add(line())
        self.toolbar.width_input.setValue(18)
        self.toolbar.font_input.setValue(40)
        self.toolbar.set_quick_color(0, "#123456")
        self.toolbar.set_hotkeys_disabled(True)
        self.toolbar.open_settings()
        self.toolbar.reset_preferences()
        self.assertIsInstance(self.toolbar.side_panel, SettingsPanel)
        self.assertEqual(self.canvas.stroke_width, 4)
        self.assertEqual(self.canvas.font_size, 28)
        self.assertEqual(self.toolbar.quick_color_values[0], "#00c8ed")
        self.assertFalse(self.toolbar.hotkeys_disabled)
        self.assertEqual(len(self.canvas.document.marks), 1)

    def test_saved_preferences_load_in_new_toolbar(self):
        self.toolbar.set_wheel_size(False)
        self.toolbar.set_cursor_highlight(True)
        self.toolbar.set_screenshot_entire(True)
        self.toolbar.set_quick_color(0, "#123456")
        self.toolbar.update_shortcut(0, QKeySequence("Ctrl+Alt+P"))
        self.toolbar.settings.sync()
        canvas = Canvas(True)
        settings = QSettings(self.toolbar.settings.fileName(), QSettings.Format.IniFormat)
        reloaded = Toolbar(canvas, settings)
        self.assertFalse(canvas.wheel_adjusts_size)
        self.assertTrue(canvas.highlight_cursor)
        self.assertTrue(reloaded.screenshot_entire)
        self.assertEqual(reloaded.quick_color_values[0], "#123456")
        self.assertEqual(reloaded.shortcuts[0].key(), QKeySequence("Ctrl+Alt+P"))
        reloaded.deleteLater()
        canvas.deleteLater()

    def test_normal_click_near_button_right_edge_switches_tool(self):
        self.canvas.show()
        self.toolbar.show()
        for _ in range(15):
            self.toolbar.select_tool("line")
            QTest.mouseClick(self.toolbar.ink_button, Qt.MouseButton.LeftButton, pos=QPoint(19,8))
            self.assertEqual(self.canvas.tool, "pen")
            self.assertIsNone(self.toolbar.side_panel)

    def test_corner_opens_attached_options_and_selection_switches(self):
        self.toolbar.show()
        QTest.mouseClick(self.toolbar.ink_button, Qt.MouseButton.LeftButton, pos=QPoint(26,26))
        self.assertIs(self.toolbar.side_panel, self.toolbar.ink_menu)
        self.assertFalse(self.toolbar.ink_menu.isWindow())
        QTest.mouseClick(self.toolbar.ink_menu.icon_buttons[1], Qt.MouseButton.LeftButton)
        self.assertEqual(self.canvas.tool, "highlighter")
        self.assertIsNone(self.toolbar.side_panel)

    def test_settings_attached_bounded_and_preserves_logo_position(self):
        self.toolbar.show()
        before = self.toolbar.logo.mapToGlobal(QPoint())
        self.toolbar.open_settings()
        panel = self.toolbar.side_panel
        self.assertIs(panel.window(), self.toolbar)
        self.assertFalse(panel.isWindow())
        self.assertLessEqual(panel.height(), self.toolbar.strip.height())
        self.assertEqual(self.toolbar.height(), self.toolbar.rail.height())
        strip_x = self.toolbar.strip.mapTo(self.toolbar, QPoint()).x()
        self.assertTrue(panel.x() == strip_x + self.toolbar.strip.width() or
                        panel.x() + panel.width() == strip_x)
        self.assertEqual(self.toolbar.logo.mapToGlobal(QPoint()), before)
        self.toolbar.close_sidebar()
        self.assertEqual(self.toolbar.logo.mapToGlobal(QPoint()), before)

    def test_all_option_panels_fit_inside_expanded_rail(self):
        self.toolbar.show()
        for menu, button in [(self.toolbar.cursor_menu,self.toolbar.ghost_button),
                             (self.toolbar.fade_menu,self.toolbar.fade_button),
                             (self.toolbar.more_menu,self.toolbar.copy_button),
                             (self.toolbar.width_menu,self.toolbar.width_button)]:
            self.toolbar.open_menu(menu, button)
            self.assertIs(menu.window(), self.toolbar)
            self.assertLessEqual(menu.height(), self.toolbar.strip.height())
            self.assertLessEqual(menu.y() + menu.height(), self.toolbar.height())
            self.toolbar.close_sidebar()

    def test_collapsed_only_logo_and_closed_eye_are_visible(self):
        self.toolbar.show()
        self.toolbar.open_settings()
        self.toolbar.collapse_toolbar()
        visible = [button for button in self.toolbar.findChildren(QToolButton) if button.isVisible()]
        self.assertEqual(set(visible), {self.toolbar.logo, self.toolbar.reopen_button})
        self.assertEqual(self.toolbar.mask().boundingRect().height(), self.toolbar.height())
        self.assertLess(self.toolbar.height(), 90)
        self.toolbar.reopen_button.click()
        self.assertTrue(self.toolbar.strip.isVisible())

    def test_clear_has_no_confirmation_and_is_undoable(self):
        self.canvas.document.add(line())
        with patch.object(self.toolbar, "message", side_effect=AssertionError("No confirmation expected")):
            self.toolbar.clear()
        self.assertEqual(len(self.canvas.document.marks), 0)
        self.canvas.document.undo()
        self.assertEqual(len(self.canvas.document.marks), 1)

    def test_logo_has_transparent_corners_and_green_ring(self):
        from screenpen.icons import ASSETS
        image = QImage(str(ASSETS / "app" / "my_pen_icon.png"))
        self.assertTrue(image.hasAlphaChannel())
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
        self.assertEqual(image.pixelColor(image.width()-1, image.height()-1).alpha(), 0)


class PerformanceRegressionTests(unittest.TestCase):
    def setUp(self):
        self.canvas = Canvas(True)
        self.canvas.resize(500, 300)

    def tearDown(self):
        self.canvas.hide()
        self.canvas.deleteLater()

    def test_committed_drawing_cache_reuses_raster(self):
        for index in range(40):
            self.canvas.document.add(line(index * 4 + 10))
        image = self.canvas.committed_layer()
        with patch("screenpen.canvas.paint_mark", side_effect=AssertionError("Static drawing repainted")):
            for _ in range(50):
                self.assertIs(self.canvas.committed_layer(), image)

    def test_idle_timer_stops_and_stationary_highlight_does_not_repaint(self):
        self.canvas.show()
        self.assertFalse(self.canvas.animation_timer.isActive())
        self.canvas.highlight_cursor = True
        self.assertTrue(self.canvas.animation_timer.isActive())
        self.canvas.animate()
        with patch.object(self.canvas, "update") as update:
            self.canvas.animate()
            self.canvas.animate()
            update.assert_not_called()
        self.canvas.hide()
        self.assertFalse(self.canvas.animation_timer.isActive())

    def test_expiry_does_not_copy_history_until_something_expires(self):
        mark = Mark("line", "#ff0000", 4, [(10,10,1),(100,10,1)], fade_after=5)
        self.canvas.document.add(mark)
        history = self.canvas.document._undo
        self.assertFalse(self.canvas.document.expire(mark.created_at + 1))
        self.assertIs(self.canvas.document._undo, history)

    def test_shift_press_and_release_updates_pending_shape(self):
        self.canvas.tool = "line"
        self.canvas.begin(QPointF(10,10))
        self.canvas.move_input(QPointF(80,40))
        global_point = self.canvas.mapToGlobal(QPoint(80,40))
        with patch("screenpen.canvas.QCursor.pos", return_value=global_point):
            QTest.keyPress(self.canvas, Qt.Key.Key_Shift)
            self.assertEqual(self.canvas.pending.points[-1][:2], (80,10))
            QTest.keyRelease(self.canvas, Qt.Key.Key_Shift)
            self.assertEqual(self.canvas.pending.points[-1][:2], (80,40))

    def test_overlay_mode_changes_keep_the_native_window(self):
        overlay = Canvas(False)
        overlay.show()
        native_id = overlay.winId()
        for _ in range(20):
            overlay.set_ghost(True)
            self.assertTrue(overlay.windowHandle().flags() & Qt.WindowType.WindowTransparentForInput)
            overlay.set_ghost(False)
            self.assertFalse(overlay.windowHandle().flags() & Qt.WindowType.WindowTransparentForInput)
            self.assertEqual(overlay.winId(), native_id)
        overlay.hide()
        overlay.deleteLater()


class StartupTests(unittest.TestCase):
    def test_linux_registration_is_removable_and_quotes_paths(self):
        from screenpen.startup import StartupManager
        with tempfile.TemporaryDirectory() as folder:
            manager = StartupManager(platform="linux", home=folder, config_home=folder,
                                     executable=folder + "/venv with spaces/python", script=folder + "/My Pen/main.py")
            self.assertFalse(manager.enabled())
            manager.set_enabled(True)
            text = manager.path().read_text()
            self.assertIn('"--background"', text)
            import shlex
            exec_line = next(line[5:] for line in text.splitlines() if line.startswith('Exec='))
            # Decode desktop-entry string escapes, then Exec argument quoting.
            argv = shlex.split(exec_line.replace('\\\\', '\\'))
            self.assertEqual(argv, manager.command())
            self.assertTrue(manager.enabled())
            manager.set_enabled(False)
            self.assertFalse(manager.enabled())

    def test_mac_registration_is_removable_and_uses_argument_array(self):
        import plistlib
        from screenpen.startup import StartupManager
        with tempfile.TemporaryDirectory() as folder:
            manager = StartupManager(platform="darwin", home=folder)
            manager.set_enabled(True)
            data = plistlib.loads(manager.path().read_bytes())
            self.assertEqual(data['ProgramArguments'][-1], '--background')
            self.assertTrue(data['RunAtLoad'])
            manager.set_enabled(False)
            self.assertFalse(manager.enabled())

    def test_windows_registration_targets_current_user_and_can_be_disabled(self):
        from contextlib import nullcontext
        from types import SimpleNamespace
        from screenpen.startup import StartupManager, RUN_KEY
        key = object()
        registry = SimpleNamespace(HKEY_CURRENT_USER=123, REG_SZ=1,
                                   CreateKey=Mock(return_value=nullcontext(key)),
                                   SetValueEx=Mock(), DeleteValue=Mock())
        manager = StartupManager(platform='win32', executable=str(Path(tempfile.gettempdir())/'mp-test'/'python.exe'),
                                 script=str(Path(tempfile.gettempdir())/'My Pen'/'main.py'))
        with patch.dict(sys.modules, {'winreg': registry}):
            manager.set_enabled(True)
            registry.CreateKey.assert_called_with(123, RUN_KEY)
            command = registry.SetValueEx.call_args.args[-1]
            self.assertIn('--background', command)
            self.assertIn(subprocess.list2cmdline([str(manager.script)]), command)
            manager.set_enabled(False)
            registry.DeleteValue.assert_called_once_with(key, 'My Pen')


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.image = QImage(400, 300, QImage.Format.Format_RGB32)
        self.image.fill(QColor("#46a1c4"))
        self.canvas = Canvas(True)
        self.selector = CaptureSelector(self.image, QRect(0, 0, 400, 300), self.canvas)

    def tearDown(self):
        self.selector.hide()
        self.selector.deleteLater()
        self.canvas.deleteLater()
        QApplication.clipboard().clear()

    def test_scaled_crop_preserves_physical_pixel_dimensions(self):
        self.image.setDevicePixelRatio(2)
        result = crop_pixels(self.image, QRect(10, 20, 100, 60))
        self.assertEqual((result.width(), result.height()), (200, 120))
        self.assertEqual(result.devicePixelRatio(), 1)
        self.assertEqual(result.pixelColor(0, 0).name(), "#46a1c4")

    def test_empty_and_out_of_bounds_crop(self):
        self.assertTrue(crop_pixels(self.image, QRect()).isNull())
        result = crop_pixels(self.image, QRect(380, 280, 100, 100))
        self.assertEqual((result.width(), result.height()), (20, 20))

    def test_selection_drag_and_copy(self):
        self.selector.show()
        QTest.mousePress(self.selector, Qt.MouseButton.LeftButton, pos=QPoint(20, 40))
        QTest.mouseMove(self.selector, QPoint(180, 140))
        QTest.mouseRelease(self.selector, Qt.MouseButton.LeftButton, pos=QPoint(180, 140))
        self.assertTrue(self.selector.actions.isVisible())
        expected = self.selector.selection.size()
        self.selector.copy()
        result = QApplication.clipboard().image()
        self.assertEqual(result.size(), expected)
        self.assertEqual(result.pixelColor(0, 0).name(), "#46a1c4")
        self.assertTrue(self.selector._finished)

    def test_save_selected_region_to_png(self):
        self.selector.selection = QRect(10, 20, 120, 80)
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "capture.png")
            def accept(dialog, canvas):
                dialog.selectFile(path)
                return QDialog.DialogCode.Accepted
            with patch("screenpen.capture.run_dialog", side_effect=accept):
                self.selector.save()
            result = QImage(path)
            self.assertEqual((result.width(), result.height()), (120, 80))
            self.assertEqual(result.pixelColor(20, 20).name(), "#46a1c4")

    def test_escape_cancels_once(self):
        calls = []
        self.selector.finished.connect(lambda: calls.append(True))
        self.selector.show()
        QTest.keyClick(self.selector, Qt.Key.Key_Escape)
        self.selector.finish()
        self.assertEqual(len(calls), 1)

    def test_automatic_screenshot_folder_and_entire_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.canvas.dialog_parent = Mock(screenshot_ask=False, screenshot_folder=tmp)
            self.selector.select_entire()
            self.assertEqual(self.selector.selection, self.selector.rect())
            self.selector.save()
            files = list(Path(tmp).glob("My_Pen_*.png"))
            self.assertEqual(len(files), 1)
            self.assertEqual(QImage(str(files[0])).size(), self.image.size())


if __name__ == "__main__":
    unittest.main()
