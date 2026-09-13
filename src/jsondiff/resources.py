"""개발 실행과 exe 실행 양쪽에서 동작하는 리소스 경로 헬퍼.

PyInstaller onefile 로 묶으면 데이터 파일이 실행 시점에 임시 폴더에 풀리고
그 경로가 sys._MEIPASS 에 들어온다. 개발 중에는 저장소의 assets/ 를 그대로 쓴다.
"""
from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    """번들 기준(또는 저장소 기준) 상대 경로를 실제 경로로 바꾼다."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / relative
    # src/jsondiff/resources.py -> 저장소 루트
    return Path(__file__).resolve().parent.parent.parent / relative


def icon_path() -> Path:
    return resource_path("assets/app.ico")
