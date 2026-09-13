#!/usr/bin/env python3
"""
여러 폴더에 흩어져 있는 같은 이름의 JSON 파일들을 한 번에 비교해서
단일 HTML 리포트로 정리한다.

사용 예:
    python json_folder_diff.py envs/dev envs/stage envs/prod -o report.html
    python json_folder_diff.py --root ./envs --recursive
    python json_folder_diff.py A B C --ignore "*/generatedAt" --ignore "*/uuid"
    python json_folder_diff.py A B C --array-id-key id
"""

from __future__ import annotations

import argparse
import fnmatch
import html
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

MISSING = "\x00__MISSING__\x00"  # 경로 자체가 없는 상태를 나타내는 표식


# ---------------------------------------------------------------- 평탄화

def _escape_token(token: str) -> str:
    """JSON Pointer 규칙에 맞게 경로 조각을 이스케이프한다."""
    return token.replace("~", "~0").replace("/", "~1")


def flatten(obj: Any, prefix: str = "", out: dict | None = None,
            array_id_key: str | None = None) -> dict[str, Any]:
    """중첩 JSON을 {경로: 리프값} 형태로 펼친다.

    빈 dict/list는 그 자체를 리프로 취급한다. 그래야 "빈 객체"와
    "키 없음"이 구분된다.
    """
    if out is None:
        out = {}

    if isinstance(obj, dict) and obj:
        for key, value in obj.items():
            flatten(value, f"{prefix}/{_escape_token(str(key))}", out, array_id_key)

    elif isinstance(obj, list) and obj:
        # 리스트 원소가 전부 dict이고 지정한 식별자 키를 갖고 있으면
        # 인덱스 대신 식별자로 매칭한다. 순서가 달라도 같은 항목끼리 비교된다.
        if array_id_key and all(
            isinstance(item, dict) and array_id_key in item for item in obj
        ):
            for item in obj:
                ident = _escape_token(str(item[array_id_key]))
                flatten(item, f"{prefix}/[{array_id_key}={ident}]", out, array_id_key)
        else:
            for index, item in enumerate(obj):
                flatten(item, f"{prefix}/{index}", out, array_id_key)

    else:
        out[prefix or "/"] = obj

    return out


def value_key(value: Any) -> str:
    """값 비교와 그룹핑에 쓰는 정규화된 문자열."""
    if value is MISSING or value == MISSING:
        return MISSING
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def type_name(value: Any) -> str:
    if value is MISSING or value == MISSING:
        return "없음"
    if value is None:
        return "null"
    return {
        bool: "boolean", int: "number", float: "number",
        str: "string", list: "array", dict: "object",
    }.get(type(value), type(value).__name__)


# ---------------------------------------------------------------- 데이터 모델

@dataclass
class ValueGroup:
    """같은 값을 가진 폴더들의 묶음."""
    display: str
    folders: list[str]
    is_missing: bool = False
    is_outlier: bool = False


@dataclass
class DiffRow:
    path: str
    kind: str                      # "값" | "타입" | "키 존재"
    groups: list[ValueGroup]


@dataclass
class FileReport:
    name: str
    rows: list[DiffRow] = field(default_factory=list)
    identical_paths: int = 0
    total_paths: int = 0
    absent_in: list[str] = field(default_factory=list)   # 파일이 아예 없는 폴더
    errors: dict[str, str] = field(default_factory=dict)  # 폴더 -> 파싱 오류

    @property
    def diff_count(self) -> int:
        return len(self.rows)

    @property
    def has_findings(self) -> bool:
        return bool(self.rows or self.absent_in or self.errors)


# ---------------------------------------------------------------- 수집 & 비교

def collect_files(pairs: list[tuple[str, Path]], pattern: str,
                  recursive: bool) -> dict[str, dict[str, Path]]:
    """{상대 파일명: {폴더라벨: 실제 경로}} 형태의 인벤토리를 만든다."""
    inventory: dict[str, dict[str, Path]] = {}
    for label, folder in pairs:
        globber = folder.rglob if recursive else folder.glob
        for path in sorted(globber(pattern)):
            if not path.is_file():
                continue
            rel = str(path.relative_to(folder))
            inventory.setdefault(rel, {})[label] = path
    return dict(sorted(inventory.items()))


def is_ignored(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)


def compare_file(name: str, sources: dict[str, Path], all_labels: list[str],
                 ignore: list[str], array_id_key: str | None) -> FileReport:
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

        # 과반을 차지하는 값이 있으면 나머지를 outlier로 표시한다.
        sizes = sorted((len(v) for v in buckets.values()), reverse=True)
        majority = sizes[0] if sizes[0] > len(live_labels) / 2 else None

        groups = []
        for vkey, labels in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
            missing = vkey == MISSING
            groups.append(ValueGroup(
                display="(키 없음)" if missing else vkey,
                folders=labels,
                is_missing=missing,
                is_outlier=majority is not None and len(labels) < majority,
            ))

        report.rows.append(DiffRow(path=json_path, kind=kind, groups=groups))

    return report


# ---------------------------------------------------------------- HTML 렌더링

CSS = """
:root{
  --paper:#F3F4F0; --surface:#FFF; --ink:#1B211E; --muted:#6E7671;
  --rule:#DCDFD8; --rule-soft:#EBEDE7;
  --agree:#2E5E52; --flag:#9A5B0E; --gone:#6F5580;
  --flag-bg:#FBF1DF; --gone-bg:#F2ECF5; --agree-bg:#E7EFEB;
}
@media (prefers-color-scheme: dark){
  :root{
    --paper:#161A18; --surface:#1E2321; --ink:#E7EAE6; --muted:#9AA39D;
    --rule:#333A36; --rule-soft:#272D2A;
    --agree:#7FBFAB; --flag:#E0AC5E; --gone:#BFA3CE;
    --flag-bg:#2E2618; --gone-bg:#272130; --agree-bg:#1F2E29;
  }
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI","Apple SD Gothic Neo",
       "Noto Sans KR",Roboto,sans-serif;
}
.wrap{max-width:1080px; margin:0 auto; padding:40px 24px 96px}
h1{font-size:26px; font-weight:650; letter-spacing:-.02em; margin:0 0 6px}
.meta{color:var(--muted); font-size:13.5px; margin:0 0 32px}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}

/* 요약: 폴더별로 혼자 튄 횟수 */
.scoreboard{border-top:2px solid var(--ink); padding-top:18px; margin-bottom:14px}
.scoreboard h2{font-size:13px; font-weight:600; color:var(--muted); margin:0 0 14px}
.score{display:grid; grid-template-columns:minmax(80px,180px) 1fr auto;
       gap:12px; align-items:center; padding:5px 0}
.score .name{font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
.track{height:9px; background:var(--rule-soft); border-radius:2px; overflow:hidden}
.fill{height:100%; background:var(--flag); border-radius:2px}
.score .n{color:var(--muted); font-size:13px; min-width:58px; text-align:right}
.hint{color:var(--muted); font-size:13px; margin:14px 0 34px}

.stats{display:flex; flex-wrap:wrap; gap:10px 26px; margin:0 0 26px;
       padding-bottom:22px; border-bottom:1px solid var(--rule)}
.stat b{font-size:21px; font-weight:650; margin-right:6px}
.stat span{color:var(--muted); font-size:13px}

/* 검색 */
.toolbar{position:sticky; top:0; z-index:5; background:var(--paper);
         padding:14px 0 12px; margin-bottom:8px; border-bottom:1px solid var(--rule)}
#q{width:100%; padding:11px 14px; border:1px solid var(--rule); border-radius:6px;
   background:var(--surface); color:var(--ink); font-size:14px}
#q:focus{outline:2px solid var(--agree); outline-offset:1px; border-color:transparent}
#hits{color:var(--muted); font-size:12.5px; margin-top:8px; min-height:1em}

details.file{background:var(--surface); border:1px solid var(--rule);
             border-radius:8px; margin:12px 0; overflow:hidden}
details.file[open]{border-color:var(--muted)}
summary{cursor:pointer; padding:14px 18px; display:flex; align-items:center;
        gap:12px; list-style:none; font-weight:600}
summary::-webkit-details-marker{display:none}
summary::before{content:"▸"; color:var(--muted); font-size:11px; transition:transform .15s}
details[open] summary::before{transform:rotate(90deg)}
summary .fname{flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
.count{font-size:12.5px; font-weight:500; color:var(--muted)}
.count.zero{color:var(--agree)}

.rows{border-top:1px solid var(--rule-soft)}
.row{padding:14px 18px; border-bottom:1px solid var(--rule-soft)}
.row:last-child{border-bottom:none}
.path{font-size:13px; word-break:break-all; margin-bottom:9px}
.kind{display:inline-block; font-size:11px; padding:1px 7px; border-radius:3px;
      margin-left:8px; vertical-align:1px; background:var(--rule-soft); color:var(--muted)}
.kind.존재{background:var(--gone-bg); color:var(--gone)}
.kind.타입{background:var(--flag-bg); color:var(--flag)}

.group{display:grid; grid-template-columns:minmax(120px,240px) 1fr;
       gap:10px 16px; padding:5px 0; align-items:baseline}
.tags{display:flex; flex-wrap:wrap; gap:4px}
.tag{font-size:11.5px; padding:2px 7px; border-radius:3px;
     background:var(--agree-bg); color:var(--agree); white-space:nowrap}
.group.outlier .tag{background:var(--flag-bg); color:var(--flag); font-weight:600}
.group.missing .tag{background:var(--gone-bg); color:var(--gone)}
.val{font-size:13px; white-space:pre-wrap; word-break:break-all; max-height:8.5em;
     overflow:auto}
.group.missing .val{color:var(--gone); font-style:italic}

.note{padding:11px 18px; font-size:13px; background:var(--gone-bg); color:var(--gone)}
.note.err{background:var(--flag-bg); color:var(--flag)}
.empty{color:var(--muted); font-size:13px; padding:14px 18px}
.hidden{display:none}
@media (max-width:640px){
  .wrap{padding:28px 16px 72px}
  .group{grid-template-columns:1fr; gap:4px}
  .score{grid-template-columns:1fr auto; }
  .score .track{display:none}
}
"""

JS = """
const q = document.getElementById('q');
const hits = document.getElementById('hits');
const files = [...document.querySelectorAll('details.file')];

function run(){
  const term = q.value.trim().toLowerCase();
  let shownRows = 0, shownFiles = 0;
  for (const file of files){
    const rows = [...file.querySelectorAll('.row')];
    let visible = 0;
    for (const row of rows){
      const match = !term || row.dataset.search.includes(term);
      row.classList.toggle('hidden', !match);
      if (match) visible++;
    }
    const nameMatch = !term || file.dataset.name.includes(term);
    const keep = visible > 0 || (nameMatch && rows.length === 0) || nameMatch;
    file.classList.toggle('hidden', !keep);
    if (keep){ shownFiles++; shownRows += visible; }
    if (term) file.open = visible > 0;
  }
  hits.textContent = term
    ? `${shownFiles}개 파일에서 ${shownRows}건 일치`
    : '';
}
q.addEventListener('input', run);
"""


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def render_html(reports: list[FileReport], labels: list[str], root_desc: str,
                ignore: list[str]) -> str:
    outlier_counts = Counter({label: 0 for label in labels})
    for report in reports:
        for row in report.rows:
            for group in row.groups:
                if group.is_outlier:
                    for label in group.folders:
                        outlier_counts[label] += 1
        for label in report.absent_in:
            outlier_counts[label] += 1

    total_diffs = sum(r.diff_count for r in reports)
    differing_files = sum(1 for r in reports if r.has_findings)
    peak = max(outlier_counts.values()) or 1

    parts: list[str] = []
    add = parts.append

    add(f"<!DOCTYPE html><html lang='ko'><head><meta charset='utf-8'>")
    add("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    add("<title>JSON 폴더 비교 리포트</title>")
    add(f"<style>{CSS}</style></head><body><div class='wrap'>")

    add("<h1>JSON 폴더 비교 리포트</h1>")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    ignore_note = f" · 무시 패턴 {len(ignore)}개" if ignore else ""
    add(f"<p class='meta'>{esc(root_desc)} · 폴더 {len(labels)}개 · {stamp}{esc(ignore_note)}</p>")

    # 스코어보드: 어느 폴더가 혼자 튀는지
    add("<section class='scoreboard'><h2>혼자 다른 값을 가진 횟수</h2>")
    for label, count in sorted(outlier_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        width = round(count / peak * 100)
        add(
            f"<div class='score'><div class='name'>{esc(label)}</div>"
            f"<div class='track'><div class='fill' style='width:{width}%'></div></div>"
            f"<div class='n'>{count}건</div></div>"
        )
    add("</section>")
    add("<p class='hint'>과반이 같은 값을 가질 때, 소수 쪽에 속한 폴더를 셉니다. "
        "파일이 아예 없는 경우도 1건으로 칩니다.</p>")

    add("<div class='stats'>")
    add(f"<div class='stat'><b>{len(reports)}</b><span>비교한 파일</span></div>")
    add(f"<div class='stat'><b>{differing_files}</b><span>차이가 있는 파일</span></div>")
    add(f"<div class='stat'><b>{total_diffs}</b><span>다른 경로</span></div>")
    add("</div>")

    add("<div class='toolbar'>")
    add("<input id='q' type='search' placeholder='파일명, 경로, 값으로 검색' "
        "autocomplete='off' spellcheck='false'>")
    add("<div id='hits'></div></div>")

    for report in reports:
        open_attr = " open" if report.has_findings and report.diff_count <= 40 else ""
        cls = "count" if report.has_findings else "count zero"
        if report.diff_count:
            label_text = f"{report.diff_count}곳 다름 · {report.identical_paths}곳 동일"
        else:
            label_text = f"모두 동일 ({report.identical_paths}곳)"

        search_blob = report.name.lower()
        add(f"<details class='file'{open_attr} data-name='{esc(search_blob)}'>")
        add(f"<summary><span class='fname mono'>{esc(report.name)}</span>"
            f"<span class='{cls}'>{esc(label_text)}</span></summary>")

        if report.absent_in:
            add(f"<div class='note'>이 파일이 없는 폴더: {esc(', '.join(report.absent_in))}</div>")
        for folder, message in report.errors.items():
            add(f"<div class='note err'>{esc(folder)} — 읽기 실패: {esc(message)}</div>")

        if report.rows:
            add("<div class='rows'>")
            for row in report.rows:
                blob = (row.path + " " + " ".join(
                    g.display + " " + " ".join(g.folders) for g in row.groups
                )).lower()
                add(f"<div class='row' data-search='{esc(blob)}'>")
                add(f"<div class='path mono'>{esc(row.path)}"
                    f"<span class='kind {esc(row.kind.split()[-1])}'>{esc(row.kind)}</span></div>")
                for group in row.groups:
                    classes = "group"
                    if group.is_outlier:
                        classes += " outlier"
                    if group.is_missing:
                        classes += " missing"
                    tags = "".join(f"<span class='tag'>{esc(f)}</span>" for f in group.folders)
                    add(f"<div class='{classes}'><div class='tags'>{tags}</div>"
                        f"<div class='val mono'>{esc(group.display)}</div></div>")
                add("</div>")
            add("</div>")
        elif not report.has_findings:
            add("<div class='empty'>모든 폴더의 내용이 같습니다.</div>")

        add("</details>")

    add(f"<script>{JS}</script></div></body></html>")
    return "".join(parts)


# ---------------------------------------------------------------- 진입점

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="여러 폴더의 같은 이름 JSON 파일들을 한 번에 비교해 HTML 리포트를 만든다.")
    parser.add_argument("folders", nargs="*", type=Path, help="비교할 폴더들 (2개 이상)")
    parser.add_argument("--root", type=Path,
                        help="이 폴더의 하위 폴더들을 비교 대상으로 삼는다")
    parser.add_argument("-o", "--output", type=Path, default=Path("json-diff-report.html"))
    parser.add_argument("--pattern", default="*.json", help="파일 검색 패턴 (기본 *.json)")
    parser.add_argument("--recursive", action="store_true", help="하위 폴더까지 탐색")
    parser.add_argument("--ignore", action="append", default=[], metavar="GLOB",
                        help="무시할 경로 패턴. 여러 번 지정 가능 (예: '*/updatedAt')")
    parser.add_argument("--array-id-key", metavar="KEY",
                        help="배열을 인덱스 대신 이 키로 매칭한다 (예: id)")
    parser.add_argument("--only-diff", action="store_true",
                        help="차이가 있는 파일만 리포트에 넣는다")
    args = parser.parse_args(argv)

    folders = list(args.folders)
    if args.root:
        folders += sorted(p for p in args.root.iterdir() if p.is_dir())
    if len(folders) < 2:
        parser.error("비교할 폴더를 2개 이상 지정하세요 (또는 --root 사용).")

    missing = [str(f) for f in folders if not f.is_dir()]
    if missing:
        parser.error("폴더를 찾을 수 없습니다: " + ", ".join(missing))

    labels = [f.name for f in folders]
    if len(set(labels)) != len(labels):
        labels = [str(f) for f in folders]  # 폴더명이 겹치면 전체 경로로 구분

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
