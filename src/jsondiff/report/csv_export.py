"""CSV 내보내기. 한 행 = (파일명, 경로, 차이유형, 폴더, 값). docs/SPEC-ui.md 참고."""
from __future__ import annotations

import csv
from pathlib import Path

from jsondiff.engine.models import FileReport


def write_csv(reports: list[FileReport], path: Path) -> None:
    """Excel 한글 깨짐을 막기 위해 utf-8-sig로 쓴다."""
    with path.open("w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.writer(fp)
        writer.writerow(["파일명", "경로", "차이유형", "폴더", "값"])
        for report in reports:
            for folder in report.absent_in:
                writer.writerow([report.name, "", "파일 없음", folder, ""])
            for folder, message in report.errors.items():
                writer.writerow([report.name, "", "읽기 실패", folder, message])
            for row in report.rows:
                for group in row.groups:
                    for folder in group.folders:
                        writer.writerow([report.name, row.path, row.kind, folder, group.display])
