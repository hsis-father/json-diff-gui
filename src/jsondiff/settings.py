"""프리셋과 마지막 세션 상태를 %APPDATA%\\JsonFolderDiff\\presets.json 에 저장한다.

UI 모듈을 import 하지 않는다(표준 라이브러리만). 설정 파일이 없거나 깨져 있어도
예외를 올리지 않고 기본값을 돌려준다. 설정 때문에 프로그램이 못 뜨는 일은 없어야 한다.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

APP_DIR_NAME = "JsonFolderDiff"
SETTINGS_FILENAME = "presets.json"
SCHEMA_VERSION = 1


@dataclass
class Options:
    pattern: str = "*.json"
    recursive: bool = False
    array_id_key: str = ""
    ignore: str = ""
    only_diff: bool = False


@dataclass
class Session:
    """폴더 목록과 옵션 한 벌. 마지막 상태와 이름 붙인 프리셋이 같은 모양을 쓴다."""

    folders: list[str] = field(default_factory=list)
    options: Options = field(default_factory=Options)


@dataclass
class Settings:
    last_session: Session = field(default_factory=Session)
    presets: dict[str, Session] = field(default_factory=dict)


def settings_dir() -> Path:
    """%APPDATA%\\JsonFolderDiff. APPDATA가 없는 환경(테스트, 비Windows)은 홈 아래로 떨어진다."""
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / ".config"
    return base / APP_DIR_NAME


def settings_path() -> Path:
    return settings_dir() / SETTINGS_FILENAME


def _session_from_dict(raw: object) -> Session:
    if not isinstance(raw, dict):
        return Session()
    folders = [str(f) for f in raw.get("folders", []) if isinstance(f, str)]
    opts_raw = raw.get("options")
    options = Options()
    if isinstance(opts_raw, dict):
        # 모르는 키는 버리고 아는 키만 받는다. 옛 파일이나 손댄 파일에도 견디게.
        known = {f.name for f in Options.__dataclass_fields__.values()}
        for key, value in opts_raw.items():
            if key in known:
                setattr(options, key, value)
    return Session(folders=folders, options=options)


def load_settings(path: Path | None = None) -> Settings:
    """설정을 읽는다. 파일이 없거나 깨졌으면 기본값."""
    target = path or settings_path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return Settings()
    if not isinstance(raw, dict):
        return Settings()

    presets_raw = raw.get("presets")
    presets = {}
    if isinstance(presets_raw, dict):
        presets = {str(name): _session_from_dict(body) for name, body in presets_raw.items()}

    return Settings(last_session=_session_from_dict(raw.get("last_session")), presets=presets)


def save_settings(settings: Settings, path: Path | None = None) -> None:
    """설정을 쓴다. 저장 실패가 프로그램을 멈추게 하지는 않는다(호출부에서 무시 가능)."""
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": SCHEMA_VERSION,
        "last_session": asdict(settings.last_session),
        "presets": {name: asdict(body) for name, body in settings.presets.items()},
    }
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
