"""Entry point. Run with: python main.py"""
import os
import sys
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from core.config import APP_NAME, APP_DISPLAY
from ui.main_window import MainWindow


def resource_path(rel: str) -> str:
    """Resolve a bundled resource path whether running from source or .exe."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.abspath("."), rel)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY)
    app.setOrganizationName("Krabby Pathy")

    icon_path = resource_path(os.path.join("assets", "logo.ico"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()