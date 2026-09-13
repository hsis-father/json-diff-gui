"""결과 뷰가 큰 리포트를 삼키지 않는지 지킨다.

QWebEngineView.setHtml()은 내용을 data: URL로 바꿔 넣고 그 URL이 2MB로 제한되기 때문에,
그보다 큰 리포트를 넣으면 아무 오류 없이 빈 화면이 된다. 폴더 10개 × 파일 200개면
실제로 그 크기를 넘으므로, 결과는 반드시 파일로 써서 file:// 로 열어야 한다.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PyQt5.QtWebEngineWidgets")

# QtWebEngineWidgets는 QApplication보다 먼저 import 되어 있어야 한다.
from PyQt5.QtWidgets import QApplication

from jsondiff.ui.main_window import MainWindow

TWO_MB = 2 * 1024 * 1024


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def window(qapp):
    win = MainWindow()
    yield win
    win.close()


def test_large_report_is_not_truncated_by_data_url_limit(window):
    big = "<html><meta charset='utf-8'><body>" + ("가" * TWO_MB) + "</body></html>"

    window._show_html(big)

    assert window._view_file.read_text(encoding="utf-8") == big
    # data: URL이 아니라 실제 파일을 열어야 2MB 제한에 걸리지 않는다.
    # load()는 비동기라 url()은 아직 비어 있다. 요청된 URL로 확인한다.
    assert window.result_view.page().requestedUrl().isLocalFile()


def test_view_file_is_cleaned_up_on_close(qapp):
    win = MainWindow()
    view_dir = win._view_dir
    assert view_dir.exists()

    win.close()

    assert not view_dir.exists()
