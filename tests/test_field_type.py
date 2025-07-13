#!/usr/bin/env python3

import pytest
from procdocs.core.field_type import FieldType


# --- Field Type Validation --- #


@pytest.mark.parametrize("value, expected", [
    ("string", FieldType.STRING),
    ("number", FieldType.NUMBER),
    ("boolean", FieldType.BOOLEAN),
    ("list", FieldType.LIST),
    ("dict", FieldType.DICT),
    ("enum", FieldType.ENUM),
])
def test_valid_parse_fieldtype(value, expected):
    assert FieldType.parse(value) == expected
    assert FieldType.parse(value.capitalize()) == expected
    assert FieldType.parse(value.upper()) == expected
    assert FieldType.parse(value.title()) == expected
    assert FieldType.parse(f"  {value}  ") == expected


@pytest.mark.parametrize("value, expected", [
    ("strng", FieldType.INVALID),
    (1, FieldType.NUMBER),
    (None, FieldType.BOOLEAN),
    (3.14, FieldType.LIST),
    (FieldType, FieldType.DICT),
    (FieldType.parse, FieldType.ENUM),
])
def test_invalid_parse_fieldtype(value, expected):
    assert FieldType.parse(value) == FieldType.INVALID
