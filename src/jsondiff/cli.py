"""argparse 진입점. `python -m jsondiff.cli --root ...`"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jsondiff.engine.compare import compare_file
from jsondiff.engine.inventory import collect_files, make_labels
from jsondiff.report.html import render_html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="여러 폴더의 같은 이름 JSON 파일들을 한 번에 비교해 HTML 리포트를 만든다."
    )
    parser.add_argument("folders", nargs="*", type=Path, help="비교할 폴더들 (2개 이상)")
    parser.add_argument("--root", type=Path, help="이 폴더의 하위 폴더들을 비교 대상으로 삼는다")
    parser.add_argument("-o", "--output", type=Path, default=Path("json-diff-report.html"))
    parser.add_argument("--pattern", default="*.json", help="파일 검색 패턴 (기본 *.json)")
    parser.add_argument("--recursive", action="store_true", help="하위 폴더까지 탐색")
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="GLOB",
        help="무시할 경로 패턴. 여러 번 지정 가능 (예: '*/updatedAt')",
    )
    parser.add_argument(
        "--array-id-key", metavar="KEY", help="배열을 인덱스 대신 이 키로 매칭한다 (예: id)"
    )
    parser.add_argument(
        "--only-diff", action="store_true", help="차이가 있는 파일만 리포트에 넣는다"
    )
    args = parser.parse_args(argv)

    folders = list(args.folders)
    if args.root:
        folders += sorted(p for p in args.root.iterdir() if p.is_dir())
    if len(folders) < 2:
        parser.error("비교할 폴더를 2개 이상 지정하세요 (또는 --root 사용).")

    missing = [str(f) for f in folders if not f.is_dir()]
    if missing:
        parser.error("폴더를 찾을 수 없습니다: " + ", ".join(missing))

    labels = make_labels(folders)

    inventory = collect_files(list(zip(labels, folders)), args.pattern, args.recursive)
    if not inventory:
        print(f"'{args.pattern}' 에 맞는 파일이 없습니다.", file=sys.stderr)
        return 1

    reports = []
    for name, sources in inventory.items():
        report = compare_file(name, sources, labels, args.ignore, args.array_id_key)
        if args.only_diff and not report.has_findings:
            continue
        reports.append(report)

    document = render_html(reports, labels, f"기준 경로 {folders[0].parent}", args.ignore)
    args.output.write_text(document, encoding="utf-8")

    diff_files = sum(1 for r in reports if r.has_findings)
    total = sum(r.diff_count for r in reports)
    print(f"파일 {len(reports)}개 비교 · 차이 있는 파일 {diff_files}개 · 다른 경로 {total}곳")
    print(f"리포트: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
