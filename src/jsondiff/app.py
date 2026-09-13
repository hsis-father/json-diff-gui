"""PyQt5 GUI 진입점. `python -m jsondiff.app`"""
from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from jsondiff.ui.main_window import MainWindow


def main() -> int:
    # 125%/150% 고DPI 환경에서 레이아웃이 깨지지 않도록 자동 스케일링을 켠다.
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setApplicationName("JSON Folder Diff")
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
