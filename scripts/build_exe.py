"""배포용 Windows 단일 실행 파일(JsonFolderDiff.exe)을 만든다.

빌드 전에 테스트·린트를 통과시키고, PyInstaller onefile로 src/jsondiff/app.py를 묶는다.
자세한 내용은 .claude/skills/build-exe/SKILL.md 참고.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
APP_ENTRY = SRC / "jsondiff" / "app.py"
ICON = ROOT / "assets" / "app.ico"
APP_NAME = "JsonFolderDiff"


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    # 실패를 예외가 아니라 종료 코드로 다뤄 어느 단계에서 멈췄는지 그대로 전달한다.
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main() -> int:
    run([sys.executable, "-m", "pytest", "-q"])
    run([sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"])

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
        "--paths",
        str(SRC),
    ]
    if ICON.exists():
        cmd += ["--icon", str(ICON)]
    run(cmd)

    exe = ROOT / "dist" / f"{APP_NAME}.exe"
    print(f"\n빌드 완료: {exe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
