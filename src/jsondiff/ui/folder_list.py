"""비교할 폴더 목록. 탐색기에서 폴더를 끌어다 놓을 수 있고, 드래그로 순서를 바꿀 수 있다.

목록의 순서가 그대로 리포트의 열 순서가 되므로, 내부 재정렬(InternalMove)만 허용하고
외부에서 온 파일 URL은 폴더인 것만 골라 addFolders로 넘긴다.
"""
from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import QListWidget, QListWidgetItem

FLASH_COLOR = QColor("#FBF1DF")  # 리포트의 --flag-bg 와 같은 색
FLASH_MS = 600
MISSING_COLOR = QColor("#9A9A9A")  # 사라진 폴더


class FolderListWidget(QListWidget):
    folders_dropped = pyqtSignal(list)  # list[Path], 탐색기에서 드롭됐을 때

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setAcceptDrops(True)
        self.setDefaultDropAction(Qt.MoveAction)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            paths = [Path(url.toLocalFile()) for url in event.mimeData().urls()]
            folders = [p for p in paths if p.is_dir()]
            if folders:
                self.folders_dropped.emit(folders)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)  # 내부 재정렬

    def folder_paths(self) -> list[Path]:
        return [Path(self.item(i).data(Qt.UserRole)) for i in range(self.count())]

    def existing_folder_paths(self) -> list[Path]:
        """실제로 존재하는 폴더만. 프리셋에 적힌 폴더가 사라졌을 수 있다."""
        return [p for p in self.folder_paths() if p.is_dir()]

    def has_path(self, path: Path) -> bool:
        return any(p == path for p in self.folder_paths())

    def add_folder(self, path: Path) -> QListWidgetItem:
        item = QListWidgetItem()
        item.setData(Qt.UserRole, str(path))
        self.addItem(item)
        self._apply_presence(item, path)
        return item

    def refresh_presence(self) -> None:
        """사라진 폴더 표시를 다시 계산한다. 프리셋을 불러온 뒤에 부른다."""
        for i in range(self.count()):
            item = self.item(i)
            self._apply_presence(item, Path(item.data(Qt.UserRole)))

    def _apply_presence(self, item: QListWidgetItem, path: Path) -> None:
        if path.is_dir():
            item.setText(f"{path.name}    {path}")
            item.setForeground(QBrush())
            item.setToolTip(str(path))
        else:
            # 지우지 않고 회색으로 남긴다. 사용자가 경로를 보고 직접 판단할 수 있어야 한다.
            item.setText(f"{path.name}    {path}    (폴더 없음 — 비교에서 제외)")
            item.setForeground(QBrush(MISSING_COLOR))
            item.setToolTip(f"{path}\n폴더를 찾을 수 없어 비교에서 제외됩니다.")

    def flash_item(self, path: Path) -> None:
        """이미 있는 폴더를 다시 추가하려고 했을 때 해당 행을 잠깐 강조한다."""
        for i in range(self.count()):
            item = self.item(i)
            if item.data(Qt.UserRole) == str(path):
                self.scrollToItem(item)
                item.setBackground(QBrush(FLASH_COLOR))
                QTimer.singleShot(FLASH_MS, lambda it=item: self._clear_flash(it))
                break

    def _clear_flash(self, item: QListWidgetItem) -> None:
        # 강조를 지우기 전에 그 사이 행이 삭제됐을 수 있다.
        if self.row(item) >= 0:
            item.setBackground(QBrush())
