"""비교 결과를 표현하는 데이터클래스. report/, ui/ 는 이 구조만 소비한다."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValueGroup:
    """같은 값을 가진 폴더들의 묶음."""

    display: str
    folders: list[str]
    is_missing: bool = False
    is_outlier: bool = False


@dataclass
class DiffRow:
    path: str
    kind: str  # "값" | "타입" | "키 존재"
    groups: list[ValueGroup]


@dataclass
class FileReport:
    name: str
    rows: list[DiffRow] = field(default_factory=list)
    identical_paths: int = 0
    total_paths: int = 0
    absent_in: list[str] = field(default_factory=list)  # 이 파일이 없는 폴더
    errors: dict[str, str] = field(default_factory=dict)  # 폴더 -> 파싱 오류

    @property
    def diff_count(self) -> int:
        return len(self.rows)

    @property
    def has_findings(self) -> bool:
        return bool(self.rows or self.absent_in or self.errors)
