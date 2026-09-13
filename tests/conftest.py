from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------- GUI 테스트 공용

# QtWebEngine은 QWebEngineView가 파괴된 뒤 새로 만들어지면 access violation으로 죽는다.
# 테스트 도중에는 창을 절대 수거하지 않도록 여기에 참조를 붙들어 둔다(세션 끝에 함께 정리).
_live_windows: list = []


@pytest.fixture(scope="session")
def qapp():
    """프로세스당 하나뿐인 QApplication. GUI 테스트 모듈들이 함께 쓴다."""
    pytest.importorskip("PyQt5.QtWebEngineWidgets")
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def make_window(qapp):
    """MainWindow를 만든다. 닫기는 하되 세션이 끝날 때까지 참조를 유지한다."""
    from jsondiff.ui.main_window import MainWindow

    def _make() -> MainWindow:
        win = MainWindow()
        _live_windows.append(win)
        return win

    yield _make


@pytest.fixture
def make_folder(tmp_path: Path):
    """{폴더명: {파일명: dict_또는_str}} 을 실제 파일 트리로 만들어 폴더 Path 리스트를 돌려준다."""

    def _make(spec: dict[str, dict[str, object]]) -> list[Path]:
        folders = []
        for folder_name, files in spec.items():
            folder = tmp_path / folder_name
            folder.mkdir()
            for filename, content in files.items():
                target = folder / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, str):
                    target.write_text(content, encoding="utf-8")
                else:
                    target.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
            folders.append(folder)
        return folders

    return _make
