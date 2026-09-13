# 비교 엔진 명세

`reference/json_folder_diff.py`에 동작하는 프로토타입이 있다. 이 문서는 그 동작을
확정된 사양으로 정리한 것이다. 구현이 이 문서와 어긋나면 문서를 고치거나 구현을 고친다.

## 1. 입력

- 비교 폴더 2~20개. 각 폴더에는 같은 이름의 JSON 파일들이 들어 있고, 내용만 다르다.
- 폴더 라벨은 폴더명을 쓴다. 폴더명이 겹치면 전체 경로를 라벨로 쓴다.
- 옵션
  - `pattern`: 파일 검색 패턴, 기본 `*.json`
  - `recursive`: 하위 폴더까지 탐색. 켜면 파일 키가 폴더 기준 상대 경로가 된다.
  - `ignore`: 무시할 경로 glob 목록 (예: `*/generatedAt`, `*/uuid`)
  - `array_id_key`: 배열 매칭에 쓸 키 이름 (예: `id`)
  - `only_diff`: 차이 없는 파일을 결과에서 제외

## 2. 인벤토리

폴더들을 스캔해 `{상대 파일명: {폴더라벨: 실제 경로}}`를 만든다. 파일명은 폴더들의 **합집합**이다.
어떤 폴더에 없는 파일도 결과에 포함하고, 없는 폴더를 `FileReport.absent_in`에 기록한다.
내용 비교보다 먼저 나오는 첫 번째 정보이므로 누락시키지 않는다.

## 3. 평탄화

각 JSON을 `{경로: 리프값}`으로 펼친다. 경로는 JSON Pointer 형식(`/db/host`)이고,
키에 포함된 `~`와 `/`는 각각 `~0`, `~1`로 이스케이프한다.

- 빈 `{}`와 빈 `[]`는 그 자체를 리프로 취급한다. "빈 객체"와 "키 없음"이 구분되어야 한다.
- 배열 기본 처리는 인덱스 기준(`/items/0/name`).
- `array_id_key`가 지정되고 **배열 원소가 전부 dict이며 전부 그 키를 가질 때만**
  인덱스 대신 식별자로 매칭한다: `/endpoints/[id=auth]/url`.
  조건을 하나라도 만족하지 않으면 조용히 인덱스 방식으로 되돌아간다.

## 4. 비교

파일 하나마다, 모든 폴더의 평탄화 결과에서 경로 합집합을 만들고 경로별로 순회한다.

1. `ignore` 패턴에 걸리면 건너뛴다 (`fnmatch`, 전체 경로 대상).
2. 폴더별 값을 모은다. 그 폴더에 경로가 없으면 `MISSING` 표식.
3. 값 비교 키는 `json.dumps(value, sort_keys=True, ensure_ascii=False)`.
   딕셔너리 키 순서 차이를 차이로 보지 않기 위함이다.
4. 모든 폴더의 값 키가 같으면 `identical_paths`만 올리고 버린다.
5. 다르면 같은 값끼리 묶어 `ValueGroup` 리스트를 만든다. 그룹은 크기 내림차순 정렬.

### 차이 유형 (`DiffRow.kind`)

| 판정 순서 | 조건 | 값 |
|---|---|---|
| 1 | 어떤 폴더에 경로 자체가 없음 | `키 존재` |
| 2 | 존재하는 값들의 타입이 둘 이상 (`30` vs `"30"`) | `타입` |
| 3 | 그 외 | `값` |

타입 이름은 `string / number / boolean / null / array / object / 없음`으로 표기한다.
Python의 `bool`은 `int`의 하위 타입이므로 `number`로 분류되지 않도록 먼저 검사한다.

### Outlier 판정

가장 큰 그룹의 크기가 **전체 폴더 수의 과반을 넘을 때만** 다수파로 인정하고,
그보다 작은 그룹들을 outlier로 표시한다. 과반이 없으면(예: 2:2:1) 아무도 outlier가 아니다.
2개 폴더만 비교할 때는 1이 과반이 아니므로 자연스럽게 outlier가 생기지 않는다.

## 5. 자료구조

```python
@dataclass
class ValueGroup:
    display: str          # 값의 JSON 표현. 키 없음이면 "(키 없음)"
    folders: list[str]    # 이 값을 가진 폴더 라벨들
    is_missing: bool
    is_outlier: bool

@dataclass
class DiffRow:
    path: str             # "/db/host"
    kind: str             # "값" | "타입" | "키 존재"
    groups: list[ValueGroup]

@dataclass
class FileReport:
    name: str
    rows: list[DiffRow]
    identical_paths: int
    total_paths: int
    absent_in: list[str]        # 이 파일이 없는 폴더
    errors: dict[str, str]      # 폴더 -> 오류 메시지
```

## 6. 집계

- 폴더별 outlier 횟수: outlier 그룹에 속한 횟수 + 파일이 아예 없는 횟수(파일당 1).
  리포트 최상단 스코어보드의 근거값이다.
- 전체 파일 수, 차이가 있는 파일 수, 다른 경로 총 개수.

## 7. 오류 처리

| 상황 | 처리 |
|---|---|
| JSON 파싱 실패 | `errors[폴더] = "메시지 (line N, col N)"`, 그 폴더만 비교에서 제외 |
| 파일 읽기 실패(권한 등) | 동일하게 `errors`에 기록 |
| 모든 폴더에서 읽기 실패 | 차이 행 없이 오류만 담은 `FileReport` 반환 |
| 패턴에 맞는 파일 0개 | 사용자에게 안내하고 종료. 빈 리포트를 만들지 않는다 |

## 8. 테스트에 반드시 넣을 케이스

- 5개 폴더 중 4개가 같고 1개만 다름 → outlier 1건
- 2:2:1 분포 → outlier 0건
- `30` vs `"30"` → `타입`
- 한 폴더에만 있는 키 → `키 존재`, 나머지 그룹은 `(키 없음)`
- `null` 값과 키 없음이 다르게 나오는지
- 빈 `{}`와 키 없음이 다르게 나오는지
- 배열 순서만 다를 때: `array_id_key` 지정 시 차이 0건, 미지정 시 차이 발생
- 배열 원소 일부에 id가 없을 때 인덱스 방식으로 폴백하는지
- 파일이 일부 폴더에만 있을 때 `absent_in`
- BOM 붙은 파일, 깨진 JSON
- 한글 키·값, 한글 폴더명, 공백 포함 경로
