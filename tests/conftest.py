from __future__ import annotations

import json
from pathlib import Path

import pytest


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
