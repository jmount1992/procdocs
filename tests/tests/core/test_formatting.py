#!/usr/bin/env python3
import pytest

from procdocs.core.formatting import format_pydantic_errors_simple, _format_error_loc


# --- Unit tests for _format_error_loc --- #

# keep the original parametrized cases, but remove the object() one
@pytest.mark.parametrize("loc,expected", [
    (("structure", 1, "fieldname"), "structure[1].fieldname"),
    ((0, "items"), "[0].items"),
    ((), "<root>"),
    ((0, 1, "x"), "[0][1].x"),
    (("a", 3, 2, "b"), "a[3][2].b"),
])
def test_format_error_loc(loc, expected):
    assert _format_error_loc(loc) == expected


def test_format_error_loc_with_non_string_segment_object_has_stable_shape():
    import re
    out = _format_error_loc(("weird", object(), "key"))
    assert re.fullmatch(r"weird\.<object object at 0x[a-fA-F0-9]+>\.key", out)


# --- format_pydantic_errors_simple: happy path with .errors() --- #

def test_format_pydantic_errors_simple_with_pydantic_like_errors():
    class FakeValidationError(Exception):
        def errors(self):
            return [
                {"loc": ("structure", 1, "fieldname"), "msg": "Field required"},
                {"loc": (0, "items"), "msg": "Extra inputs are not permitted"},
                {"loc": (), "msg": "Invalid payload"},
            ]

    exc = FakeValidationError("ignored string")
    msgs = format_pydantic_errors_simple(exc)
    assert msgs == [
        "structure[1].fieldname: Field required",
        "[0].items: Extra inputs are not permitted",
        "<root>: Invalid payload",
    ]


# --- format_pydantic_errors_simple: fallback when .errors() missing --- #

def test_format_pydantic_errors_simple_without_errors_attr_uses_str_first_line():
    exc = ValueError("Boom!\nDetails that should be ignored")
    assert format_pydantic_errors_simple(exc) == ["Boom!"]


# --- format_pydantic_errors_simple: fallback when .errors() raises --- #

def test_format_pydantic_errors_simple_when_errors_method_raises_uses_str_first_line():
    class Exploding(Exception):
        def errors(self):
            raise RuntimeError("nope")

    exc = Exploding("Top line only\nand the rest")
    assert format_pydantic_errors_simple(exc) == ["Top line only"]
