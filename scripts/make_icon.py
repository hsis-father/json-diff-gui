"""assets/app.ico 를 만든다.

아이콘 뜻: 나란히 놓인 폴더 N개 중 하나만 색이 다르다 = 이 도구가 찾아주는 것.
Qt의 ICO 저장은 한 크기만 담기므로, 크기별 PNG를 그려 ICO 컨테이너를 직접 조립한다.
(Vista 이상은 ICO 안에 PNG를 넣는 형식을 지원한다.)
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from PyQt5.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PyQt5.QtGui import QColor, QImage, QPainter
from PyQt5.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "app.ico"

SIZES = [16, 24, 32, 48, 64, 128, 256]

INK = QColor("#1B211E")  # 배경
AGREE = QColor("#7FBFAB")  # 다수파 폴더
FLAG = QColor("#E0AC5E")  # 혼자 다른 폴더


def render(size: int) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)

    # 둥근 사각형 배경
    painter.setBrush(INK)
    radius = size * 0.22
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    # 막대 3개. 작은 크기에서도 "셋 중 하나가 다르다"가 보이도록 여백을 넉넉히 둔다.
    margin = size * 0.18
    gap = size * 0.07
    bar_w = (size - margin * 2 - gap * 2) / 3
    top = size * 0.26
    bar_h = size - top - margin
    bar_r = min(bar_w * 0.35, size * 0.08)

    for index in range(3):
        painter.setBrush(FLAG if index == 2 else AGREE)
        x = margin + index * (bar_w + gap)
        # 마지막 막대만 조금 짧게 그려 색 말고 모양으로도 구분되게 한다.
        height = bar_h * (0.62 if index == 2 else 1.0)
        y = top + (bar_h - height)
        painter.drawRoundedRect(QRectF(x, y, bar_w, height), bar_r, bar_r)

    painter.end()
    return image


def png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def build_ico(images: list[QImage]) -> bytes:
    payloads = [png_bytes(img) for img in images]

    header = struct.pack("<HHH", 0, 1, len(payloads))  # reserved, type=icon, count
    offset = len(header) + 16 * len(payloads)

    entries = []
    for image, payload in zip(images, payloads):
        side = 0 if image.width() >= 256 else image.width()  # 256은 0으로 적는 규약
        entries.append(
            struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(payload), offset)
        )
        offset += len(payload)

    return header + b"".join(entries) + b"".join(payloads)


def main() -> int:
    app = QApplication(sys.argv)  # QImage/QPainter 사용에 필요
    OUT.parent.mkdir(parents=True, exist_ok=True)

    images = [render(size) for size in SIZES]
    OUT.write_bytes(build_ico(images))

    # 눈으로 확인할 수 있게 가장 큰 크기를 PNG로도 남긴다
    images[-1].save(str(OUT.with_suffix(".png")), "PNG")

    print(f"아이콘 생성: {OUT} ({OUT.stat().st_size:,} bytes, {len(SIZES)}개 크기)")
    del app
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
