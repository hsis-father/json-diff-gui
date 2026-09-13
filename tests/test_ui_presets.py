"""프리셋 저장/복원과 사라진 폴더 처리. 4단계."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PyQt5.QtWebEngineWidgets")

from jsondiff.settings import Options, Session


@pytest.fixture
def window(make_window, tmp_path, monkeypatch):
    # 실제 %APPDATA% 를 건드리지 않도록 설정 경로를 임시 폴더로 돌린다.
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return make_window()


def test_session_roundtrip_through_ui(window, tmp_path):
    a, b = tmp_path / "dev", tmp_path / "prod"
    a.mkdir()
    b.mkdir()

    window._apply_session(
        Session(
            folders=[str(a), str(b)],
            options=Options(pattern="*.conf", recursive=True, array_id_key="id", only_diff=True),
        )
    )
    captured = window._current_session()

    assert [Path(f) for f in captured.folders] == [a, b]
    assert captured.options.pattern == "*.conf"
    assert captured.options.recursive is True
    assert captured.options.array_id_key == "id"
    assert captured.options.only_diff is True


def test_missing_folder_is_kept_but_excluded(window, tmp_path):
    alive, gone = tmp_path / "alive", tmp_path / "gone"
    alive.mkdir()

    window._apply_session(Session(folders=[str(alive), str(gone)]))

    # 목록에는 남지만 비교 대상에서는 빠진다
    assert len(window.folder_list.folder_paths()) == 2
    assert window.folder_list.existing_folder_paths() == [alive]
    assert "폴더 없음" in window.folder_list.item(1).text()


def test_run_disabled_when_only_one_folder_still_exists(window, tmp_path):
    alive, gone = tmp_path / "alive", tmp_path / "gone"
    alive.mkdir()

    window._apply_session(Session(folders=[str(alive), str(gone)]))

    assert not window.run_btn.isEnabled()


def test_preset_is_saved_and_reloaded_from_disk(window, make_window, tmp_path):
    a, b = tmp_path / "x", tmp_path / "y"
    a.mkdir()
    b.mkdir()
    window._apply_session(Session(folders=[str(a), str(b)], options=Options(pattern="*.cfg")))

    window._settings.presets["환경 비교"] = window._current_session()
    window._persist_settings()

    # 새 창을 띄우면 디스크에서 다시 읽어야 한다
    fresh = make_window()
    assert "환경 비교" in fresh._settings.presets
    assert fresh._settings.presets["환경 비교"].options.pattern == "*.cfg"
    assert fresh.preset_combo.findText("환경 비교") > 0


def test_last_session_restored_on_next_launch(window, make_window, tmp_path):
    a, b = tmp_path / "p", tmp_path / "q"
    a.mkdir()
    b.mkdir()
    window._apply_session(Session(folders=[str(a), str(b)], options=Options(only_diff=True)))

    window.close()  # closeEvent 가 마지막 상태를 저장한다

    fresh = make_window()
    assert [Path(f) for f in fresh._settings.last_session.folders] == [a, b]
    assert fresh.only_diff_check.isChecked() is True
