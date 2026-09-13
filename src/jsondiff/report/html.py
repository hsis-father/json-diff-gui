"""HTML 리포트 렌더러. CLI·GUI 공용. 오프라인 단일 파일이어야 하므로
CDN·웹폰트·외부 이미지를 링크하지 않는다."""
from __future__ import annotations

import html
from collections import Counter
from datetime import datetime

from jsondiff.engine.models import FileReport

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


def render_html(
    reports: list[FileReport], labels: list[str], root_desc: str, ignore: list[str]
) -> str:
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

    add("<!DOCTYPE html><html lang='ko'><head><meta charset='utf-8'>")
    add("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    add("<title>JSON 폴더 비교 리포트</title>")
    add(f"<style>{CSS}</style></head><body><div class='wrap'>")

    add("<h1>JSON 폴더 비교 리포트</h1>")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")  # noqa: DTZ005 (표시용 로컬 시각)
    ignore_note = f" · 무시 패턴 {len(ignore)}개" if ignore else ""
    add(f"<p class='meta'>{esc(root_desc)} · 폴더 {len(labels)}개 · {stamp}{esc(ignore_note)}</p>")

    add("<section class='scoreboard'><h2>혼자 다른 값을 가진 횟수</h2>")
    for label, count in sorted(outlier_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        width = round(count / peak * 100)
        add(
            f"<div class='score'><div class='name'>{esc(label)}</div>"
            f"<div class='track'><div class='fill' style='width:{width}%'></div></div>"
            f"<div class='n'>{count}건</div></div>"
        )
    add("</section>")
    add(
        "<p class='hint'>과반이 같은 값을 가질 때, 소수 쪽에 속한 폴더를 셉니다. "
        "파일이 아예 없는 경우도 1건으로 칩니다.</p>"
    )

    add("<div class='stats'>")
    add(f"<div class='stat'><b>{len(reports)}</b><span>비교한 파일</span></div>")
    add(f"<div class='stat'><b>{differing_files}</b><span>차이가 있는 파일</span></div>")
    add(f"<div class='stat'><b>{total_diffs}</b><span>다른 경로</span></div>")
    add("</div>")

    add("<div class='toolbar'>")
    add(
        "<input id='q' type='search' placeholder='파일명, 경로, 값으로 검색' "
        "autocomplete='off' spellcheck='false'>"
    )
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
        add(
            f"<summary><span class='fname mono'>{esc(report.name)}</span>"
            f"<span class='{cls}'>{esc(label_text)}</span></summary>"
        )

        if report.absent_in:
            add(f"<div class='note'>이 파일이 없는 폴더: {esc(', '.join(report.absent_in))}</div>")
        for folder, message in report.errors.items():
            add(f"<div class='note err'>{esc(folder)} — 읽기 실패: {esc(message)}</div>")

        if report.rows:
            add("<div class='rows'>")
            for row in report.rows:
                blob = (
                    row.path
                    + " "
                    + " ".join(g.display + " " + " ".join(g.folders) for g in row.groups)
                ).lower()
                add(f"<div class='row' data-search='{esc(blob)}'>")
                add(
                    f"<div class='path mono'>{esc(row.path)}"
                    f"<span class='kind {esc(row.kind.split()[-1])}'>{esc(row.kind)}</span></div>"
                )
                for group in row.groups:
                    classes = "group"
                    if group.is_outlier:
                        classes += " outlier"
                    if group.is_missing:
                        classes += " missing"
                    tags = "".join(f"<span class='tag'>{esc(f)}</span>" for f in group.folders)
                    add(
                        f"<div class='{classes}'><div class='tags'>{tags}</div>"
                        f"<div class='val mono'>{esc(group.display)}</div></div>"
                    )
                add("</div>")
            add("</div>")
        elif not report.has_findings:
            add("<div class='empty'>모든 폴더의 내용이 같습니다.</div>")

        add("</details>")

    add(f"<script>{JS}</script></div></body></html>")
    return "".join(parts)
