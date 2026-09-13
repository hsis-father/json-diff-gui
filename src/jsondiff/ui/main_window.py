"""단일 창, 세로 3단 레이아웃. docs/SPEC-ui.md 참고 (원래 pywebview 명세를 PyQt5로 옮김)."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jsondiff.engine.models import FileReport
from jsondiff.report.csv_export import write_csv
from jsondiff.report.html import render_html
from jsondiff.ui.folder_list import FolderListWidget
from jsondiff.ui.worker import CompareWorker

# charset 선언이 없으면 file:// 로 열 때 한글이 깨진다 (setHtml과 달리 UTF-8을 가정하지 않는다).
PLACEHOLDER_HTML = """
<html><head><meta charset="utf-8"></head>
<body style="font:14px -apple-system,'Segoe UI','Malgun Gothic',sans-serif;
color:#6E7671; padding:40px;">
폴더를 2개 이상 추가하고 비교를 실행하세요.
</body></html>
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("JSON Folder Diff")
        self.setAcceptDrops(True)
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        self._worker: CompareWorker | None = None
        self._last_reports: list[FileReport] = []
        self._last_html: str = ""

        # 결과는 항상 이 임시 파일을 통해 보여준다. _show_html() 주석 참고.
        self._view_dir = Path(tempfile.mkdtemp(prefix="jsondiff-view-"))
        self._view_file = self._view_dir / "report.html"

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        layout.addWidget(self._build_folder_section())
        layout.addWidget(self._build_options_section())
        layout.addWidget(self._build_result_section(), stretch=1)

        self._update_run_enabled()
        self._show_html(PLACEHOLDER_HTML)

    def _show_html(self, html: str) -> None:
        """결과 뷰에 HTML을 띄운다.

        setHtml()을 쓰지 않는다. setHtml()은 내부적으로 내용을 data: URL로 바꿔 넣는데
        그 URL이 2MB로 제한되어, 그보다 큰 리포트는 아무 오류도 없이 빈 화면이 된다.
        폴더 10개 × 파일 200개면 리포트가 2MB를 넘기므로 실제로 걸리는 한계다.
        """
        self._view_file.write_text(html, encoding="utf-8")
        self.result_view.load(QUrl.fromLocalFile(str(self._view_file)))

    # ------------------------------------------------------------ 폴더 목록

    def _build_folder_section(self) -> QGroupBox:
        box = QGroupBox("비교할 폴더")
        outer = QVBoxLayout(box)

        top = QHBoxLayout()
        top.addWidget(QLabel("드래그해서 여러 폴더를 한 번에 놓을 수 있습니다"))
        top.addStretch(1)
        add_btn = QPushButton("폴더 추가")
        add_btn.clicked.connect(self._on_add_folder_clicked)
        remove_btn = QPushButton("선택 삭제")
        remove_btn.clicked.connect(self._on_remove_selected_clicked)
        top.addWidget(remove_btn)
        top.addWidget(add_btn)
        outer.addLayout(top)

        self.folder_list = FolderListWidget()
        self.folder_list.folders_dropped.connect(self._add_folders)
        self.folder_list.model().rowsInserted.connect(lambda *_: self._update_run_enabled())
        self.folder_list.model().rowsRemoved.connect(lambda *_: self._update_run_enabled())
        outer.addWidget(self.folder_list)

        return box

    def _on_add_folder_clicked(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "비교할 폴더 선택")
        if path:
            self._add_folders([Path(path)])

    def _on_remove_selected_clicked(self) -> None:
        for item in self.folder_list.selectedItems():
            self.folder_list.takeItem(self.folder_list.row(item))
        self._update_run_enabled()

    def _add_folders(self, folders: list[Path]) -> None:
        for folder in folders:
            # 표기만 다른 같은 폴더(.. 포함 경로 등)를 중복으로 잡아내기 위해 정규화한다.
            resolved = folder.resolve()
            if self.folder_list.has_path(resolved):
                self.folder_list.flash_item(resolved)
                continue
            self.folder_list.add_folder(resolved)
        self._update_run_enabled()

    # 창 전체도 드롭 대상 (SPEC-ui.md: 창 전체가 드롭 대상)
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            paths = [Path(url.toLocalFile()) for url in event.mimeData().urls()]
            folders = [p for p in paths if p.is_dir()]
            if folders:
                self._add_folders(folders)
            event.acceptProposedAction()

    # ------------------------------------------------------------ 옵션

    def _build_options_section(self) -> QGroupBox:
        box = QGroupBox("옵션")
        outer = QVBoxLayout(box)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("파일 패턴"))
        self.pattern_edit = QLineEdit("*.json")
        self.pattern_edit.setMaximumWidth(160)
        row1.addWidget(self.pattern_edit)
        self.recursive_check = QCheckBox("하위 폴더 포함")
        row1.addWidget(self.recursive_check)
        row1.addStretch(1)
        outer.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("배열 매칭 키"))
        self.array_id_key_edit = QLineEdit()
        self.array_id_key_edit.setPlaceholderText("id")
        self.array_id_key_edit.setMaximumWidth(120)
        row2.addWidget(self.array_id_key_edit)
        self.only_diff_check = QCheckBox("차이 없는 파일 숨기기")
        row2.addWidget(self.only_diff_check)
        row2.addStretch(1)
        outer.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("무시할 경로"))
        self.ignore_edit = QLineEdit()
        self.ignore_edit.setPlaceholderText("*/generatedAt, */uuid")
        row3.addWidget(self.ignore_edit)
        outer.addLayout(row3)

        row4 = QHBoxLayout()
        self.status_label = QLabel("")
        row4.addWidget(self.status_label)
        row4.addStretch(1)
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        self.cancel_btn.hide()
        row4.addWidget(self.cancel_btn)
        self.run_btn = QPushButton("비교 실행")
        self.run_btn.clicked.connect(self._on_run_clicked)
        row4.addWidget(self.run_btn)
        outer.addLayout(row4)

        return box

    def _update_run_enabled(self) -> None:
        count = self.folder_list.count()
        if count < 2:
            self.run_btn.setEnabled(False)
            self.status_label.setText(f"폴더를 2개 이상 추가하세요 (현재 {count}개)")
        else:
            self.run_btn.setEnabled(True)
            self.status_label.setText(f"폴더 {count}개 준비됨")

    # ------------------------------------------------------------ 결과

    def _build_result_section(self) -> QGroupBox:
        box = QGroupBox("결과")
        outer = QVBoxLayout(box)

        top = QHBoxLayout()
        top.addStretch(1)
        self.save_html_btn = QPushButton("HTML 저장")
        self.save_html_btn.clicked.connect(self._on_save_html_clicked)
        self.save_html_btn.setEnabled(False)
        self.save_csv_btn = QPushButton("CSV 저장")
        self.save_csv_btn.clicked.connect(self._on_save_csv_clicked)
        self.save_csv_btn.setEnabled(False)
        top.addWidget(self.save_html_btn)
        top.addWidget(self.save_csv_btn)
        outer.addLayout(top)

        self.result_view = QWebEngineView()
        outer.addWidget(self.result_view)

        return box

    # ------------------------------------------------------------ 비교 실행

    def _on_run_clicked(self) -> None:
        folders = self.folder_list.folder_paths()
        ignore = [p.strip() for p in self.ignore_edit.text().split(",") if p.strip()]

        # 이전 결과를 먼저 버린다. 이번 실행이 실패해도 저장 버튼이 옛 결과를 가리키면 안 된다.
        self._last_reports = []
        self._last_html = ""
        self.save_html_btn.setEnabled(False)
        self.save_csv_btn.setEnabled(False)

        self.run_btn.setEnabled(False)
        self.run_btn.setText("비교 중…")
        self.cancel_btn.show()

        self._worker = CompareWorker(
            folders=folders,
            pattern=self.pattern_edit.text().strip() or "*.json",
            recursive=self.recursive_check.isChecked(),
            ignore=ignore,
            array_id_key=self.array_id_key_edit.text().strip(),
            only_diff=self.only_diff_check.isChecked(),
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_cancel_clicked(self) -> None:
        # 스레드가 실제로 멈출 때까지 기다린 뒤에 버튼을 되살린다. 기다리지 않으면
        # 아직 파일을 읽고 있는 워커를 그대로 둔 채 다음 실행이 시작될 수 있다.
        self._stop_worker()
        self._reset_run_button()
        self.status_label.setText("취소되었습니다.")

    def _stop_worker(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(5000)

    def closeEvent(self, event) -> None:
        self._stop_worker()
        shutil.rmtree(self._view_dir, ignore_errors=True)
        super().closeEvent(event)

    def _on_progress(self, done: int, total: int) -> None:
        self.run_btn.setText(f"비교 중… ({done}/{total} 파일)")

    def _on_finished(self, reports: list[FileReport], labels: list[str]) -> None:
        self._reset_run_button()
        self._last_reports = reports

        if not reports:
            self.status_label.setText("차이가 있는 파일이 없습니다 (숨기기 옵션 적용됨).")
            self._show_html(
                "<html><meta charset='utf-8'>"
                "<body style='font:14px sans-serif; color:#6E7671; padding:40px;'>"
                "선택한 폴더들의 JSON 내용이 모두 같습니다.</body></html>"
            )
            return

        root_desc = f"폴더 {len(labels)}개 비교"
        ignore = [p.strip() for p in self.ignore_edit.text().split(",") if p.strip()]
        self._last_html = render_html(reports, labels, root_desc, ignore)
        self._show_html(self._last_html)

        diff_files = sum(1 for r in reports if r.has_findings)
        total_diffs = sum(r.diff_count for r in reports)
        self.status_label.setText(
            f"파일 {len(reports)}개 비교 · 차이 있는 파일 {diff_files}개 · 다른 경로 {total_diffs}곳"
        )
        self.save_html_btn.setEnabled(True)
        self.save_csv_btn.setEnabled(True)

    def _on_failed(self, message: str) -> None:
        self._reset_run_button()
        QMessageBox.warning(self, "비교 실패", message)
        self.status_label.setText(message)

    def _reset_run_button(self) -> None:
        self.run_btn.setText("비교 실행")
        self._update_run_enabled()
        self.cancel_btn.hide()

    # ------------------------------------------------------------ 저장

    def _on_save_html_clicked(self) -> None:
        if not self._last_html:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "HTML로 저장", "json-diff-report.html", "HTML 파일 (*.html)"
        )
        if not path:
            return
        Path(path).write_text(self._last_html, encoding="utf-8")

    def _on_save_csv_clicked(self) -> None:
        if not self._last_reports:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "CSV로 저장", "json-diff-report.csv", "CSV 파일 (*.csv)"
        )
        if not path:
            return
        write_csv(self._last_reports, Path(path))
