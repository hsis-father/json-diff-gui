from __future__ import annotations

import json
from pathlib import Path

from jsondiff.engine.compare import compare_file
from jsondiff.engine.inventory import collect_files, make_labels


def _sources(folders: list[Path], filename: str) -> dict[str, Path]:
    """폴더 리스트에서 해당 파일명이 실제로 존재하는 폴더만 sources로 뽑는다."""
    labels = make_labels(folders)
    out: dict[str, Path] = {}
    for label, folder in zip(labels, folders):
        candidate = folder / filename
        if candidate.exists():
            out[label] = candidate
    return out, labels


def test_outlier_when_one_of_five_differs(make_folder):
    spec = {name: {"a.json": {"v": 1}} for name in ["f1", "f2", "f3", "f4"]}
    spec["f5"] = {"a.json": {"v": 2}}
    folders = make_folder(spec)
    sources, labels = _sources(folders, "a.json")

    report = compare_file("a.json", sources, labels, [], None)

    assert report.diff_count == 1
    row = report.rows[0]
    outliers = [g for g in row.groups if g.is_outlier]
    assert len(outliers) == 1
    assert outliers[0].folders == ["f5"]


def test_no_outlier_when_distribution_is_2_2_1(make_folder):
    spec = {
        "f1": {"a.json": {"v": 1}},
        "f2": {"a.json": {"v": 1}},
        "f3": {"a.json": {"v": 2}},
        "f4": {"a.json": {"v": 2}},
        "f5": {"a.json": {"v": 3}},
    }
    folders = make_folder(spec)
    sources, labels = _sources(folders, "a.json")

    report = compare_file("a.json", sources, labels, [], None)

    row = report.rows[0]
    assert all(not g.is_outlier for g in row.groups)


def test_number_vs_string_is_type_diff(make_folder):
    folders = make_folder(
        {"f1": {"a.json": {"v": 30}}, "f2": {"a.json": {"v": "30"}}}
    )
    sources, labels = _sources(folders, "a.json")

    report = compare_file("a.json", sources, labels, [], None)

    assert report.rows[0].kind == "타입"


def test_key_only_in_one_folder_is_kind_exists(make_folder):
    folders = make_folder({"f1": {"a.json": {"v": 1}}, "f2": {"a.json": {}}})
    sources, labels = _sources(folders, "a.json")

    report = compare_file("a.json", sources, labels, [], None)

    row = report.rows[0]
    assert row.kind == "키 존재"
    missing_group = next(g for g in row.groups if g.is_missing)
    assert missing_group.display == "(키 없음)"


def test_null_differs_from_missing_key(make_folder):
    # w는 두 폴더 공통 키로 둬서 diff가 v 하나에만 집중되게 한다.
    folders = make_folder(
        {"f1": {"a.json": {"v": None, "w": 1}}, "f2": {"a.json": {"w": 1}}}
    )
    sources, labels = _sources(folders, "a.json")

    report = compare_file("a.json", sources, labels, [], None)

    assert report.diff_count == 1
    assert report.rows[0].kind == "키 존재"


def test_empty_object_differs_from_missing_key(make_folder):
    folders = make_folder(
        {"f1": {"a.json": {"v": {}, "w": 1}}, "f2": {"a.json": {"w": 1}}}
    )
    sources, labels = _sources(folders, "a.json")

    report = compare_file("a.json", sources, labels, [], None)

    assert report.diff_count == 1
    assert report.rows[0].kind == "키 존재"


def test_array_order_ignored_with_id_key(make_folder):
    folders = make_folder(
        {
            "f1": {"a.json": {"items": [{"id": "x", "v": 1}, {"id": "y", "v": 2}]}},
            "f2": {"a.json": {"items": [{"id": "y", "v": 2}, {"id": "x", "v": 1}]}},
        }
    )
    sources, labels = _sources(folders, "a.json")

    report = compare_file("a.json", sources, labels, [], "id")

    assert report.diff_count == 0


def test_array_order_causes_diff_without_id_key(make_folder):
    folders = make_folder(
        {
            "f1": {"a.json": {"items": [{"id": "x", "v": 1}, {"id": "y", "v": 2}]}},
            "f2": {"a.json": {"items": [{"id": "y", "v": 2}, {"id": "x", "v": 1}]}},
        }
    )
    sources, labels = _sources(folders, "a.json")

    report = compare_file("a.json", sources, labels, [], None)

    assert report.diff_count > 0


def test_array_id_key_fallback_to_index_when_partial(make_folder):
    folders = make_folder(
        {
            "f1": {"a.json": {"items": [{"id": "x", "v": 1}, {"v": 2}]}},
            "f2": {"a.json": {"items": [{"id": "x", "v": 1}, {"v": 2}]}},
        }
    )
    sources, labels = _sources(folders, "a.json")

    report = compare_file("a.json", sources, labels, [], "id")

    assert report.diff_count == 0  # 폴백된 인덱스 경로 기준으로 둘 다 동일


def test_absent_in_when_file_missing_in_some_folders(make_folder):
    folders = make_folder({"f1": {"a.json": {"v": 1}}, "f2": {}})
    labels = make_labels(folders)
    inventory = collect_files(list(zip(labels, folders)), "*.json", False)
    sources = inventory["a.json"]

    report = compare_file("a.json", sources, labels, [], None)

    assert report.absent_in == ["f2"]


def test_bom_file_parses_correctly(tmp_path: Path):
    folder1 = tmp_path / "f1"
    folder1.mkdir()
    (folder1 / "a.json").write_bytes("﻿".encode() + b'{"v": 1}')
    folder2 = tmp_path / "f2"
    folder2.mkdir()
    (folder2 / "a.json").write_text(json.dumps({"v": 1}), encoding="utf-8")

    labels = make_labels([folder1, folder2])
    inventory = collect_files(list(zip(labels, [folder1, folder2])), "*.json", False)
    report = compare_file("a.json", inventory["a.json"], labels, [], None)

    assert report.diff_count == 0
    assert not report.errors


def test_broken_json_reports_error_but_keeps_others(tmp_path: Path):
    folder1 = tmp_path / "f1"
    folder1.mkdir()
    (folder1 / "a.json").write_text("{ not valid json", encoding="utf-8")
    folder2 = tmp_path / "f2"
    folder2.mkdir()
    (folder2 / "a.json").write_text(json.dumps({"v": 1}), encoding="utf-8")

    labels = make_labels([folder1, folder2])
    inventory = collect_files(list(zip(labels, [folder1, folder2])), "*.json", False)
    report = compare_file("a.json", inventory["a.json"], labels, [], None)

    assert "f1" in report.errors
    assert report.total_paths == 1  # f2만 비교 대상에 남음
    assert report.identical_paths == 1


def test_korean_keys_values_and_folder_names(make_folder):
    folders = make_folder(
        {
            "개발": {"설정.json": {"이름": "값1"}},
            "운영 서버": {"설정.json": {"이름": "값2"}},
        }
    )
    sources, labels = _sources(folders, "설정.json")

    report = compare_file("설정.json", sources, labels, [], None)

    assert report.diff_count == 1
    assert set(labels) == {"개발", "운영 서버"}
