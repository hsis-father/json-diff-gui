from __future__ import annotations

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


def test_recursive_uses_relative_path(tmp_path):
    folder = tmp_path / "f1"
    (folder / "nested").mkdir(parents=True)
    (folder / "nested" / "a.json").write_text("{}", encoding="utf-8")

    inventory = collect_files([("f1", folder)], "*.json", True)

    assert "nested/a.json" in inventory or "nested\\a.json" in inventory
