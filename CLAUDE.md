# JSON Folder Diff

여러 폴더에 흩어진 **같은 이름의 JSON 파일들을 N개 동시에 비교**해서 차이를 보여주는
Windows 데스크톱 도구. 최종 산출물은 더블클릭으로 실행되는 단일 `.exe`.

핵심 사용 시나리오: 환경별 설정 폴더(dev / stage / qa / prod-us / prod-eu)를 한 번에 열어
"어느 환경만 값이 다른가"를 찾는 것. 1:1 비교가 아니라 N개 동시 비교가 이 도구의 존재 이유다.

## 명령어

```powershell
python -m jsondiff.cli --root .\sample\envs -o report.html   # CLI 실행
python -m jsondiff.app                                        # GUI 실행 (PyQt5)
pytest -q                                                     # 테스트
ruff check src tests scripts                                  # 린트
python scripts\build_exe.py                                   # exe 빌드
```

## 구조

```
src/jsondiff/
  engine/flatten.py    JSON → {경로: 리프값} 평탄화
  engine/compare.py    N개 폴더 동시 비교, 값 그룹핑, outlier 판정
  engine/inventory.py  폴더 스캔, 파일명 합집합
  engine/models.py     DiffRow / ValueGroup / FileReport 데이터클래스
  report/html.py       HTML 리포트 렌더러 (CLI·GUI 공용)
  report/csv_export.py CSV 내보내기
  cli.py               argparse 진입점
  app.py               PyQt5 GUI 진입점
  ui/main_window.py    메인 창 (폴더 목록 / 옵션 / 결과 3단 레이아웃)
  ui/folder_list.py    드래그앤드롭 폴더 목록 위젯
  ui/worker.py         비교를 돌리는 QThread 워커
```

## 규칙

- **엔진은 UI를 모른다.** `engine/`과 `report/`는 PyQt5 등 UI 모듈을 import 하지 않는다.
  GUI는 엔진을 호출하기만 한다. 이 경계가 깨지면 CLI가 죽는다.
- **엔진은 표준 라이브러리만 사용한다.** 서드파티 의존성은 GUI(PyQt5, PyQtWebEngine)와
  빌드(pyinstaller), 테스트(pytest, ruff)에만 허용한다. `deepdiff` 같은 비교 라이브러리를 새로 넣지 않는다.
- **결과 화면은 QWebEngineView로 HTML 리포트를 그대로 렌더링한다.** 리포트에 내장된 검색용 JS가
  그대로 동작하므로 GUI 쪽에서 검색·필터를 따로 구현하지 않는다.
- 비교 결과는 항상 `FileReport` 리스트로 먼저 만들고, 출력 포맷은 그 위에 얹는다.
  HTML·CSV·콘솔이 각자 비교 로직을 갖지 않게 한다.
- 파일 읽기는 `encoding="utf-8-sig"`. 실무 JSON에 BOM이 자주 붙는다.
- 예외로 프로그램을 죽이지 않는다. 파싱 실패·권한 오류는 해당 파일의 `FileReport.errors`에
  담아 리포트에 표시한다. 폴더 하나가 깨져도 나머지 비교는 끝까지 진행한다.
- 사용자에게 보이는 문자열(UI 라벨, 오류 메시지, 리포트 헤더)은 한국어. 코드·주석·커밋은 영어.
- 새 기능을 넣기 전에 `tests/`에 케이스를 먼저 추가한다. 특히 배열 매칭과 키 존재 여부.

## 하지 말 것

- 폴더 2개 전제로 코드를 짜지 말 것. 항상 N개(2~20)를 가정한다.
- 폴더끼리 1:1로 짝지어(5C2) 비교하지 말 것. 경로마다 N개 값을 한 번에 그룹핑한다.
- 리포트 HTML에 CDN·웹폰트·외부 이미지를 링크하지 말 것. 오프라인 단일 파일이어야 한다.
- `print()`로 GUI 상태를 알리지 말 것. GUI는 콘솔이 없다.

## 참고 문서

작업 전에 해당 문서를 읽는다. 토큰 절약을 위해 자동 로드하지 않으니 직접 열 것.

- 비교 로직·자료구조 명세 → `docs/SPEC-engine.md`
- 화면 구성·상호작용 → `docs/SPEC-ui.md`
- 작업 순서와 진행 상황 → `docs/ROADMAP.md` (한 단계 끝날 때마다 체크박스를 갱신한다)
- 이식할 기존 구현 → `reference/json_folder_diff.py` (동작 검증된 프로토타입, 여기서 로직을 가져온다)
