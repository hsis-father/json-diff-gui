"""N개 폴더 동시 비교, 값 그룹핑, outlier 판정. docs/SPEC-engine.md 4절."""
from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import Any

from jsondiff.engine.flatten import MISSING, flatten, type_name, value_key
from jsondiff.engine.models import DiffRow, FileReport, ValueGroup


def is_ignored(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)


def compare_file(
    name: str,
    sources: dict[str, Path],
    all_labels: list[str],
    ignore: list[str],
    array_id_key: str | None,
) -> FileReport:
    """파일 하나를 비교한다.

    sources에 없는(=all_labels 중 이 파일이 없는) 폴더는 absent_in에 남고,
    실제 비교는 이 파일을 가진 폴더(live_labels)끼리만 수행한다.
    """
    report = FileReport(name=name)
    report.absent_in = [label for label in all_labels if label not in sources]

    flattened: dict[str, dict[str, Any]] = {}
    for label, path in sources.items():
        try:
            with path.open(encoding="utf-8-sig") as fp:
                data = json.load(fp)
        except json.JSONDecodeError as exc:
            report.errors[label] = f"{exc.msg} (line {exc.lineno}, col {exc.colno})"
            continue
        except OSError as exc:
            report.errors[label] = str(exc)
            continue
        flattened[label] = flatten(data, array_id_key=array_id_key)

    if not flattened:
        return report

    # 파싱에 성공한 폴더끼리만 비교한다 (읽기 실패한 폴더는 errors에 남고 비교에서 빠진다).
    live_labels = [label for label in all_labels if label in flattened]
    all_paths = sorted({p for flat in flattened.values() for p in flat})

    for json_path in all_paths:
        if is_ignored(json_path, ignore):
            continue
        report.total_paths += 1

        values = {label: flattened[label].get(json_path, MISSING) for label in live_labels}
        keys = {label: value_key(value) for label, value in values.items()}

        if len(set(keys.values())) == 1:
            report.identical_paths += 1
            continue

        # 같은 값끼리 묶는다. 등장 순서를 유지해야 리포트가 안정적이다.
        buckets: dict[str, list[str]] = {}
        for label in live_labels:
            buckets.setdefault(keys[label], []).append(label)

        has_missing = MISSING in buckets
        types = {type_name(v) for v in values.values() if value_key(v) != MISSING}
        if has_missing:
            kind = "키 존재"
        elif len(types) > 1:
            kind = "타입"
        else:
            kind = "값"

        # 과반을 차지하는 값이 있을 때만 나머지를 outlier로 표시한다 (2:2:1 같은 분포는 outlier 없음).
        sizes = sorted((len(v) for v in buckets.values()), reverse=True)
        majority = sizes[0] if sizes[0] > len(live_labels) / 2 else None

        groups = []
        for vkey, labels in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
            missing = vkey == MISSING
            groups.append(
                ValueGroup(
                    display="(키 없음)" if missing else vkey,
                    folders=labels,
                    is_missing=missing,
                    is_outlier=majority is not None and len(labels) < majority,
                )
            )

        report.rows.append(DiffRow(path=json_path, kind=kind, groups=groups))

    return report
