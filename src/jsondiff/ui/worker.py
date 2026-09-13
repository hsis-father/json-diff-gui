"""비교를 워커 스레드에서 돌린다. UI를 블로킹하지 않기 위해서."""
from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from jsondiff.engine.compare import compare_file
from jsondiff.engine.inventory import collect_files, make_labels
from jsondiff.engine.models import FileReport


class CompareWorker(QThread):
    progress = pyqtSignal(int, int)  # (완료 파일 수, 전체 파일 수)
    finished_ok = pyqtSignal(list, list)  # (FileReport 리스트, 폴더 라벨 리스트)
    failed = pyqtSignal(str)

    def __init__(
        self,
        folders: list[Path],
        pattern: str,
        recursive: bool,
        ignore: list[str],
        array_id_key: str | None,
        only_diff: bool,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._folders = folders
        self._pattern = pattern
        self._recursive = recursive
        self._ignore = ignore
        self._array_id_key = array_id_key or None
        self._only_diff = only_diff
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            labels = make_labels(self._folders)
            inventory = collect_files(
                list(zip(labels, self._folders)), self._pattern, self._recursive
            )
            if not inventory:
                # 어떤 패턴으로 어디를 찾았는지 같이 알린다 (docs/SPEC-ui.md).
                where = "\n".join(f"  - {f}" for f in self._folders)
                scope = "하위 폴더까지" if self._recursive else "폴더 바로 아래에서만"
                self.failed.emit(
                    f"'{self._pattern}' 패턴에 맞는 파일을 찾지 못했습니다.\n"
                    f"찾은 범위: {scope}\n{where}"
                )
                return

            total = len(inventory)
            reports: list[FileReport] = []
            for done, (name, sources) in enumerate(inventory.items(), start=1):
                if self._cancelled:
                    return
                report = compare_file(name, sources, labels, self._ignore, self._array_id_key)
                if not (self._only_diff and not report.has_findings):
                    reports.append(report)
                self.progress.emit(done, total)

            if self._cancelled:
                return
            self.finished_ok.emit(reports, labels)
        except Exception as exc:  # noqa: BLE001 (최상위 진입점, 사용자 메시지로 변환)
            self.failed.emit(f"비교 중 오류가 발생했습니다: {exc}")
