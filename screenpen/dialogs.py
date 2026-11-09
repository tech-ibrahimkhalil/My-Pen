"""Modal dialogs must never compete with the desktop overlay for input/stacking."""
from contextlib import contextmanager

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog


@contextmanager
def suspended_overlay(canvas):
    popup = QApplication.activePopupWidget()
    if popup:
        popup.hide()
    was_visible = canvas.isVisible()
    owner = getattr(canvas, "dialog_parent", None)
    panel = getattr(owner, "side_panel", None)
    panel_visible = panel is not None and panel.isVisible()
    if panel_visible:
        panel.hide()
    if was_visible:
        canvas.hide()
    try:
        yield
    finally:
        if was_visible:
            canvas.show()
            if owner:
                owner.raise_()
            if not canvas.ghost:
                canvas.activateWindow()
        if panel_visible and getattr(owner, "side_panel", None) is panel:
            panel.show()
            panel.raise_()


def run_dialog(dialog: QDialog, canvas) -> int:
    """Hide input-blocking overlay, show owned topmost modal, always restore canvas."""
    with suspended_overlay(canvas):
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        # QMessageBox.setWindowModality rebuilds its flags; apply topmost AFTER it.
        dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        dialog.setWindowIcon(canvas.windowIcon())
        dialog.adjustSize()
        screen = dialog.screen() or QApplication.primaryScreen()
        bounds = screen.availableGeometry()
        dialog.move(bounds.center() - dialog.rect().center())

        def foreground():
            if dialog.isVisible():
                dialog.raise_()
                dialog.activateWindow()
                dialog.setFocus()

        QTimer.singleShot(0, foreground)
        return dialog.exec()
