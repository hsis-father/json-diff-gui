"""JSON -> {경로: 리프값} 평탄화. docs/SPEC-engine.md 3절."""
from __future__ import annotations

import json
from typing import Any

# 경로 자체가 없는 상태를 나타내는 표식. 실제 JSON 값과 충돌하지 않도록 제어 문자를 섞는다.
MISSING = "\x00__MISSING__\x00"


def _escape_token(token: str) -> str:
    """JSON Pointer 규칙에 맞게 경로 조각을 이스케이프한다."""
    return token.replace("~", "~0").replace("/", "~1")


def flatten(
    obj: Any,
    prefix: str = "",
    out: dict[str, Any] | None = None,
    array_id_key: str | None = None,
) -> dict[str, Any]:
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
        # 인덱스 대신 식별자로 매칭한다. 순서만 바뀐 배열이 전부 차이로 잡히는 걸 막는다.
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
    """값 비교와 그룹핑에 쓰는 정규화된 문자열. 딕셔너리 키 순서 차이는 무시한다."""
    if value is MISSING or value == MISSING:
        return MISSING
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def type_name(value: Any) -> str:
    """bool은 int의 하위 타입이므로 number보다 먼저 검사한다."""
    if value is MISSING or value == MISSING:
        return "없음"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    return {
        int: "number",
        float: "number",
        str: "string",
        list: "array",
        dict: "object",
    }.get(type(value), type(value).__name__)
