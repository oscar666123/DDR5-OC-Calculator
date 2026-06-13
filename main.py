from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.ui_main import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("DDR5 OC Calculator")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
