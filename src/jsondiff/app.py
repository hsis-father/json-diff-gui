"""PyQt5 GUI 진입점. `python -m jsondiff.app`"""
from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox

from jsondiff import __version__
from jsondiff.resources import icon_path
from jsondiff.ui.main_window import MainWindow


def main() -> int:
    # 125%/150% 고DPI 환경에서 레이아웃이 깨지지 않도록 자동 스케일링을 켠다.
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("JSON Folder Diff")
    app.setApplicationVersion(__version__)

    icon = icon_path()
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    try:
        window = MainWindow()
    except Exception as exc:  # noqa: BLE001 (최상위 진입점)
        # --windowed 빌드에는 콘솔이 없다. 예외를 삼키면 아무 일도 안 일어난 것처럼 보인다.
        QMessageBox.critical(None, "실행 실패", f"창을 띄우지 못했습니다.\n\n{exc}")
        return 1

    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
