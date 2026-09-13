from __future__ import annotations

from pathlib import Path

from jsondiff.settings import (
    Options,
    Session,
    Settings,
    load_settings,
    save_settings,
    settings_path,
)


def test_roundtrip(tmp_path: Path):
    path = tmp_path / "presets.json"
    settings = Settings(
        last_session=Session(
            folders=[r"C:\envs\dev", r"C:\envs\운영 서버"],
            options=Options(pattern="*.conf", recursive=True, array_id_key="id", only_diff=True),
        ),
        presets={"환경 비교": Session(folders=[r"C:\a"], options=Options(ignore="*/uuid"))},
    )

    save_settings(settings, path)
    loaded = load_settings(path)

    assert loaded.last_session.folders == [r"C:\envs\dev", r"C:\envs\운영 서버"]
    assert loaded.last_session.options.pattern == "*.conf"
    assert loaded.last_session.options.recursive is True
    assert loaded.presets["환경 비교"].options.ignore == "*/uuid"


def test_missing_file_returns_defaults(tmp_path: Path):
    loaded = load_settings(tmp_path / "없는파일.json")

    assert loaded.last_session.folders == []
    assert loaded.last_session.options.pattern == "*.json"
    assert loaded.presets == {}


def test_corrupt_file_returns_defaults(tmp_path: Path):
    path = tmp_path / "presets.json"
    path.write_text("{ 이건 JSON이 아니다", encoding="utf-8")

    loaded = load_settings(path)

    assert loaded.last_session.folders == []
    assert loaded.presets == {}


def test_unknown_option_keys_are_ignored(tmp_path: Path):
    """손댄 설정 파일이나 옛 버전 파일에도 견뎌야 한다."""
    path = tmp_path / "presets.json"
    path.write_text(
        '{"last_session": {"folders": ["C:\\\\x"], '
        '"options": {"pattern": "*.yaml", "미래옵션": 123}}}',
        encoding="utf-8",
    )

    loaded = load_settings(path)

    assert loaded.last_session.options.pattern == "*.yaml"
    assert not hasattr(loaded.last_session.options, "미래옵션")


def test_save_creates_parent_directory(tmp_path: Path):
    path = tmp_path / "깊은" / "경로" / "presets.json"

    save_settings(Settings(), path)

    assert path.exists()


def test_settings_path_is_under_appdata(monkeypatch):
    monkeypatch.setenv("APPDATA", r"C:\Users\tester\AppData\Roaming")

    assert settings_path() == Path(r"C:\Users\tester\AppData\Roaming\JsonFolderDiff\presets.json")
