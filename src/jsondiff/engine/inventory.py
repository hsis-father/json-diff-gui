"""폴더 스캔, 파일명 합집합. docs/SPEC-engine.md 2절."""
from __future__ import annotations

from pathlib import Path


def make_labels(folders: list[Path]) -> list[str]:
    """폴더 라벨은 폴더명을 쓴다. 겹치면 전체 경로로 구분한다."""
    labels = [f.name for f in folders]
    if len(set(labels)) != len(labels):
        labels = [str(f) for f in folders]
    return labels


def collect_files(
    pairs: list[tuple[str, Path]], pattern: str, recursive: bool
) -> dict[str, dict[str, Path]]:
    """{상대 파일명: {폴더라벨: 실제 경로}} 형태의 인벤토리를 만든다.

    파일명은 폴더들의 합집합이다. 없는 폴더는 여기서는 그냥 빠지고,
    compare 단계에서 absent_in으로 채워진다.
    """
    inventory: dict[str, dict[str, Path]] = {}
    for label, folder in pairs:
        globber = folder.rglob if recursive else folder.glob
        for path in sorted(globber(pattern)):
            if not path.is_file():
                continue
            rel = str(path.relative_to(folder))
            inventory.setdefault(rel, {})[label] = path
    return dict(sorted(inventory.items()))
