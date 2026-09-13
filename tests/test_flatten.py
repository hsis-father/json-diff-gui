from __future__ import annotations

from jsondiff.engine.flatten import MISSING, flatten, type_name, value_key


def test_flatten_nested_object():
    assert flatten({"db": {"host": "a", "port": 5432}}) == {
        "/db/host": "a",
        "/db/port": 5432,
    }


def test_empty_object_and_array_are_leaves():
    """빈 {}와 빈 []는 그 자체가 리프다. '키 없음'과 구분되어야 한다."""
    out = flatten({"a": {}, "b": []})
    assert out == {"/a": {}, "/b": []}


def test_array_index_default():
    out = flatten({"items": [{"name": "x"}, {"name": "y"}]})
    assert out == {"/items/0/name": "x", "/items/1/name": "y"}


def test_array_id_key_matching_when_all_have_key():
    out = flatten(
        {"endpoints": [{"id": "auth", "url": "u1"}, {"id": "billing", "url": "u2"}]},
        array_id_key="id",
    )
    assert out == {
        "/endpoints/[id=auth]/id": "auth",
        "/endpoints/[id=auth]/url": "u1",
        "/endpoints/[id=billing]/id": "billing",
        "/endpoints/[id=billing]/url": "u2",
    }


def test_array_id_key_falls_back_to_index_if_any_item_missing_key():
    """배열 원소 일부에 id가 없으면 조용히 인덱스 방식으로 되돌아간다."""
    out = flatten(
        {"items": [{"id": "a", "v": 1}, {"v": 2}]},
        array_id_key="id",
    )
    assert out == {"/items/0/id": "a", "/items/0/v": 1, "/items/1/v": 2}


def test_array_id_key_falls_back_when_item_not_dict():
    out = flatten({"items": [{"id": "a"}, "plain-string"]}, array_id_key="id")
    assert out == {"/items/0/id": "a", "/items/1": "plain-string"}


def test_escape_token_for_tilde_and_slash_keys():
    out = flatten({"a/b": {"c~d": 1}})
    assert out == {"/a~1b/c~0d": 1}


def test_value_key_distinguishes_type():
    assert value_key(30) != value_key("30")


def test_value_key_missing_sentinel():
    assert value_key(MISSING) == MISSING


def test_type_name_bool_is_not_number():
    """bool은 int의 서브클래스이므로 number로 분류되면 안 된다."""
    assert type_name(True) == "boolean"
    assert type_name(1) == "number"


def test_type_name_null_vs_missing():
    assert type_name(None) == "null"
    assert type_name(MISSING) == "없음"
