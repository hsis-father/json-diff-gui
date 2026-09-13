---
name: build-exe
description: JSON Folder Diff를 배포용 Windows 단일 실행 파일로 빌드하고 검증한다. 사용자가 exe 빌드, 패키징, 배포판 만들기, PyInstaller를 언급할 때 사용한다.
---

# exe 빌드

## 순서

1. 빌드 전에 `pytest -q`와 `ruff check src tests`를 먼저 통과시킨다. 실패하면 빌드하지 않는다.
2. `python scripts/build_exe.py` 실행. 이 스크립트가 PyInstaller를 호출한다.
3. 산출물은 `dist/JsonFolderDiff.exe` 하나. 다른 파일이 함께 필요하면 빌드 설정이 잘못된 것이다.

## PyInstaller 설정에서 놓치기 쉬운 것

- GUI는 PyQt5 + `QWebEngineView`다. `pyinstaller-hooks-contrib`가 `PyQt5.QtWebEngineWidgets`용
  훅을 갖고 있어 대개 자동으로 Qt WebEngine 리소스(`QtWebEngineProcess.exe`, `.pak` 파일 등)를
  같이 담아준다. onefile로 빌드했는데 결과 창이 빈 화면이면 이 리소스 누락을 먼저 의심한다.
- `--windowed`(콘솔 없음)로 빌드한다. 이 상태에서는 `print()`와 `sys.stdout`이 없다.
  콘솔 출력에 의존하는 코드가 남아 있으면 여기서 죽는다.
- 아이콘은 `--icon assets/app.ico`. `.png`는 받지 않는다.
- 백신 오탐이 잦다. onefile 빌드는 실행 시 임시 폴더에 자기를 푸는데, 이걸 의심하는 제품이 있다.
  배포 전에 최소 한 곳에서 실행해 본다.
- `QWebEngineView`를 포함하면 exe 용량이 100MB를 훌쩍 넘는다(Chromium 엔진 포함). 정상이다.

## 빌드 후 검증

파이썬이 설치되지 않은 Windows 머신에서 확인한다. 개발 머신에서만 되는 빌드는 검증된 게 아니다.

- [ ] 더블클릭으로 창이 뜨는가
- [ ] 폴더 3개를 추가하고 비교 실행이 끝까지 도는가
- [ ] 리포트가 `QWebEngineView` 안에 렌더링되는가 (여기서 실패하면 대개 WebEngine 리소스 누락)
- [ ] HTML 저장과 CSV 저장이 동작하는가
- [ ] 한글 폴더명, 공백 포함 경로에서 동작하는가
- [ ] 프리셋이 `%APPDATA%`에 쓰이고 재실행 시 복원되는가 (4단계 이후)

## QWebEngineView가 빈 화면일 때

pywebview와 달리 시스템 WebView2 런타임에 의존하지 않는다 — Chromium이 exe 안에 통째로
들어있다. 그래도 빈 화면이면 대개 PyInstaller가 `Qt5WebEngineCore.dll`이나
`QtWebEngineProcess.exe`, `resources/`, `translations/` 중 하나를 누락한 경우다.
`dist/JsonFolderDiff/` (onedir로 임시 빌드해서 확인하면 원인 파악이 쉽다) 안에 저 파일들이
실제로 있는지 먼저 확인한다.
