"""배포용 Windows 단일 실행 파일(JsonFolderDiff.exe)을 만든다.

빌드 전에 테스트·린트를 통과시키고, PyInstaller onefile로 src/jsondiff/app.py를 묶는다.
자세한 내용은 .claude/skills/build-exe/SKILL.md 참고.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from jsondiff import __version__

APP_ENTRY = SRC / "jsondiff" / "app.py"
ASSETS = ROOT / "assets"
ICON = ASSETS / "app.ico"
APP_NAME = "JsonFolderDiff"


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    # 실패를 예외가 아니라 종료 코드로 다뤄 어느 단계에서 멈췄는지 그대로 전달한다.
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    if result.returncode != 0:
        sys.exit(result.returncode)


def version_tuple() -> str:
    parts = [int(p) for p in __version__.split(".")]
    while len(parts) < 4:
        parts.append(0)
    return f"({parts[0]}, {parts[1]}, {parts[2]}, {parts[3]})"


def write_version_file(target: Path) -> None:
    """탐색기 '속성 > 자세히'에 나오는 버전 정보 리소스."""
    target.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple()},
    prodvers={version_tuple()},
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '041204B0',
        [StringStruct('CompanyName', ''),
         StringStruct('FileDescription', 'JSON Folder Diff - 여러 폴더의 JSON 비교'),
         StringStruct('FileVersion', '{__version__}'),
         StringStruct('InternalName', '{APP_NAME}'),
         StringStruct('OriginalFilename', '{APP_NAME}.exe'),
         StringStruct('ProductName', 'JSON Folder Diff'),
         StringStruct('ProductVersion', '{__version__}')])
    ]),
    VarFileInfo([VarStruct('Translation', [0x0412, 1200])])
  ]
)
""",
        encoding="utf-8",
    )


def main() -> int:
    run([sys.executable, "-m", "pytest", "-q"])
    run([sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"])

    if not ICON.exists():
        run([sys.executable, str(ROOT / "scripts" / "make_icon.py")])

    with tempfile.TemporaryDirectory() as tmp:
        version_file = Path(tmp) / "version_info.txt"
        write_version_file(version_file)

        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            str(APP_ENTRY),
            "--name",
            APP_NAME,
            "--onefile",
            "--windowed",
            "--noconfirm",
            "--clean",
            "--paths",
            str(SRC),
            # 창 아이콘을 런타임에 읽어야 하므로 데이터로도 넣는다 (exe 아이콘과 별개).
            "--add-data",
            f"{ICON};assets",
            "--icon",
            str(ICON),
            "--version-file",
            str(version_file),
        ]
        run(cmd)

    exe = ROOT / "dist" / f"{APP_NAME}.exe"
    size_mb = exe.stat().st_size / 1024 / 1024 if exe.exists() else 0
    print(f"\n빌드 완료: {exe} ({size_mb:.0f} MB, v{__version__})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
