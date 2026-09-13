from __future__ import annotations

from pathlib import Path

from jsondiff.engine.inventory import collect_files, make_labels


def test_file_union_across_folders(make_folder):
    folders = make_folder(
        {
            "f1": {"a.json": {"v": 1}, "b.json": {"v": 1}},
            "f2": {"a.json": {"v": 1}},
        }
    )
    labels = make_labels(folders)
    inventory = collect_files(list(zip(labels, folders)), "*.json", False)

    assert set(inventory.keys()) == {"a.json", "b.json"}
    assert set(inventory["a.json"].keys()) == {"f1", "f2"}
    assert set(inventory["b.json"].keys()) == {"f1"}


def test_duplicate_folder_names_fall_back_to_full_path(make_folder, tmp_path):
    sub1 = tmp_path / "group1" / "same"
    sub2 = tmp_path / "group2" / "same"
    sub1.mkdir(parents=True)
    sub2.mkdir(parents=True)

    labels = make_labels([sub1, sub2])

    assert labels == [str(sub1), str(sub2)]


def test_unc_paths_survive_resolve_and_labeling():
    """네트워크 경로(\\\\server\\share)가 경로 정규화에서 망가지지 않아야 한다.

    실제 공유 없이도 확인 가능한 부분만 본다. resolve()가 UNC 접두어를 잃으면
    드라이브 문자가 붙어 엉뚱한 로컬 경로가 된다.
    """
    unc = Path(r"\\fileserver\share\envs\dev")

    assert str(unc.resolve()).startswith("\\\\")
    assert make_labels([unc, Path(r"\\fileserver\share\envs\운영 서버")]) == ["dev", "운영 서버"]
    # 서버만 다르고 폴더명이 같으면 전체 경로로 구분해야 한다
    assert make_labels([Path(r"\\srv1\share\dev"), Path(r"\\srv2\share\dev")]) == [
        r"\\srv1\share\dev",
        r"\\srv2\share\dev",
    ]


def test_recursive_uses_relative_path(tmp_path):
    folder = tmp_path / "f1"
    (folder / "nested").mkdir(parents=True)
    (folder / "nested" / "a.json").write_text("{}", encoding="utf-8")

    inventory = collect_files([("f1", folder)], "*.json", True)

    assert "nested/a.json" in inventory or "nested\\a.json" in inventory
