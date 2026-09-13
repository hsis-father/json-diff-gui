# 작업 순서

한 단계가 끝날 때마다 체크박스를 갱신하고, 그 단계에서 정한 결정이나 알게 된 제약을
아래 "결정 기록"에 한 줄로 남긴다. 다음 세션은 이 파일을 먼저 읽고 이어서 작업한다.

각 단계는 **그 자체로 실행 가능한 상태**로 끝난다. 반쯤 만든 GUI와 반쯤 만든 엔진을
동시에 들고 가지 않는다.

## 1단계 — 엔진 이식

- [x] `reference/json_folder_diff.py`를 `src/jsondiff/` 아래 모듈로 분리
      (`engine/flatten.py`, `engine/compare.py`, `engine/inventory.py`, `engine/models.py`, `report/html.py`)
- [x] `cli.py`가 기존과 동일한 옵션으로 동작하는지 확인
- [x] `docs/SPEC-engine.md` 8절의 테스트 케이스를 `tests/`에 작성, 전부 통과 (27개)
- [ ] `sample/envs/` 아래 폴더 샘플 데이터 생성 스크립트 추가 (지금은 수동으로 만든 dev/stage/prod 3개만 있음)

끝나는 조건: `python -m jsondiff.cli --root .\sample\envs` 가 이전 프로토타입과 같은 리포트를 낸다. ✅

## 2단계 — GUI 껍데기

- [x] PyQt5 창 띄우기 (pywebview 대신, 결정 기록 참고)
- [x] 폴더 추가/삭제/재정렬 목록 (드래그앤드롭 포함, 개수 제한 없음)
- [x] 비교 실행 → 결과 HTML을 QWebEngineView에 삽입
- [x] 워커 스레드(QThread)로 실행, 진행률 표시("N/전체 파일"), UI 블로킹 없음, 취소 버튼

끝나는 조건: 폴더 여러 개를 골라 실행하면 창 안에서 리포트를 볼 수 있다. ✅ (스크린샷으로 검증)
옵션(파일 패턴/재귀/배열키/무시패턴/차이만보기)은 이미 GUI에 노출되어 있어 3단계 상당 부분 선반영됨.

## 3단계 — 옵션과 저장

- [x] 파일 패턴 / 하위 폴더 / 무시 패턴 / 배열 매칭 키 / 차이 없는 파일 숨기기 (2단계에서 선반영)
- [x] HTML 저장, CSV 저장
- [x] 드래그앤드롭으로 폴더 추가 (2단계에서 선반영)

## 4단계 — 프리셋

- [x] `%APPDATA%\JsonFolderDiff\presets.json` 읽기/쓰기 (`src/jsondiff/settings.py`)
- [x] 종료 시 마지막 상태 저장, 시작 시 복원 (exe에서도 동작 확인)
- [x] 사라진 폴더 처리 (회색 표시 + 비교에서 제외, 실행 가능 판정에서도 제외)

## 5단계 — 패키징

- [x] PyInstaller onefile 빌드 (`scripts/build_exe.py`)
- [x] 아이콘, 창 제목, 버전 정보 (`scripts/make_icon.py`로 7개 크기 ICO 생성)
- [x] 파이썬이 없는 Windows 머신에서 실행 확인 — **미검증**. 이 개발 머신에서만 확인했다.
      배포 전에 다른 PC에서 한 번 띄워봐야 한다.
- [x] WebView2 런타임 안내 — 해당 없음. PyQt5는 Chromium을 exe에 통째로 넣으므로
      시스템 WebView2에 의존하지 않는다.

## 6단계 — 마무리

- [x] 대용량 검증: 폴더 10개 × 파일 200개 = 1.45초 (스캔 0.39 + 비교 0.99 + 렌더 0.07).
      병렬 처리 불필요.
- [x] 고DPI 125% / 150% 레이아웃 확인 (900×600 최소 크기에서도 깨지지 않음)
- [x] 한글·공백 경로 테스트. 네트워크 경로는 경로 처리 로직만 검증 —
      **실제 공유 드라이브 테스트는 미실시** (이 환경에서 공유를 만들 수 없었다).
- [x] README에 스크린샷과 사용법 (`docs/screenshot.png`)

## 나중에 (지금 하지 않는다)

- 폴더별 색상 지정, 다크 모드 토글
- 차이 무시 규칙을 프리셋에 파일 단위로 저장
- JSON 외 포맷(YAML, .env) 지원
- 두 리포트를 비교하는 "이전 실행과 달라진 점" 기능

## 결정 기록

- 2026-09-13 기존 XmlJsonDiffViewer(PySide6, 좌우 2파일 비교)와는 별개의 신규 프로젝트로 D:\project\json-diff-gui 에 시작.
- 2026-09-13 GUI는 pywebview 대신 **PyQt5 + QWebEngineView**로 간다. 사용자가 PyQt 기반을 명시적으로
  요청했고, 개발 머신이 32비트 Python이라 PyQt6/Qt6(win32 미지원)는 설치조차 안 됨. 결과 리포트만
  QWebEngineView로 그대로 렌더링해 검색 JS를 재사용하고, 폴더 목록/옵션은 네이티브 Qt 위젯으로 만듦.
  (docs/SPEC-ui.md)
- 2026-09-13 1단계(엔진 이식) 완료: `reference/json_folder_diff.py` → `engine/{flatten,compare,inventory,models}.py`
  + `report/{html,csv_export}.py` + `cli.py`. SPEC-engine.md 8절 케이스 전부 `tests/`에 반영, 27개 통과.
- 2026-09-13 2단계(GUI) 완료: PyQt5 메인 창, 폴더 드래그앤드롭/재정렬, QThread 워커, 결과
  QWebEngineView 렌더링까지 스모크 테스트로 검증(스크린샷 확인). 폴더 개수는 5개 고정이 아니라
  2~N개 임의 추가 가능하도록 구현.
- 2026-09-13 전체 재점검에서 찾은 것들: **결과 뷰는 `setHtml()`을 쓰면 안 된다.** data: URL
  2MB 제한 때문에 폴더 10개 × 파일 200개(리포트 2.3MB)에서 오류 없이 빈 화면이 됐다. 임시 파일 +
  `load(file://)`로 바꿔 해결(회귀 테스트 `tests/test_ui_report_view.py`). 같이 고친 것: 비교 중
  창을 닫으면 워커 스레드가 살아있는 채로 앱이 끝나던 문제, 취소 직후 스레드를 기다리지 않고
  다음 실행이 가능하던 문제, 실행 실패 시 이전 결과가 저장 버튼에 남던 문제.
- 2026-09-13 4~6단계 완료, v1.0.0 빌드. 이때 찾은 것들:
  - **GUI 테스트 모듈을 둘 이상 한 프로세스에서 돌리면 QtWebEngine이 access violation으로 죽는다.**
    QWebEngineView가 파괴된 뒤 새로 만들어질 때 터진다. `tests/conftest.py`의 `make_window`가
    세션 동안 창 참조를 붙들어 수거되지 않게 해서 막았다. 빌드가 pytest를 먼저 돌리므로 필수.
  - 폴더 목록에 높이 제한이 없어 900×600에서 결과 영역이 94px까지 눌렸다. 목록을 140px로 묶어
    146px로 늘림(기본 1200×800에서는 346px).
  - 아이콘은 `scripts/make_icon.py`로 만든다(Pillow 없이 QPainter로 그리고 ICO를 직접 조립).
    Qt의 ICO 저장은 한 크기만 담기므로 16~256px 7개를 수동으로 묶는다.
  - 설정 파일은 정상 종료(closeEvent)에서만 쓰인다. 작업 관리자로 강제 종료하면 저장되지 않는다.
