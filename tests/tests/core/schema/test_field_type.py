#!/usr/bin/env python3
import pytest

from procdocs.core.schema.field_type import FieldType


# --- Parser Helpers --- #

@pytest.mark.parametrize("raw,expected", [
    ("string", FieldType.STRING),
    (" String ", FieldType.STRING),
    ("NUMBER", FieldType.NUMBER),
    ("boolean", FieldType.BOOLEAN),
    ("list", FieldType.LIST),
    ("dict", FieldType.DICT),
    ("enum", FieldType.ENUM),
    ("ref", FieldType.REF),
    (FieldType.STRING, FieldType.STRING),
    (None, FieldType.INVALID),
    ("unknown", FieldType.INVALID),
    (123, FieldType.INVALID),
])
def test_parsers(raw, expected):
    assert FieldType.parse(raw) is expected
    if expected == FieldType.INVALID:
        assert FieldType.try_parse(raw) is None
    else:
        assert FieldType.try_parse(raw) is expected


# --- From Python Type --- #

@pytest.mark.parametrize("typ,expected", [
    (str, FieldType.STRING),
    (int, FieldType.NUMBER),
    (float, FieldType.NUMBER),
    (bool, FieldType.BOOLEAN),
    (list, FieldType.LIST),
    (dict, FieldType.DICT),
    (set, FieldType.INVALID),
    (tuple, FieldType.INVALID),
])
def test_from_python_type(typ, expected):
    assert FieldType.from_python_type(typ) is expected


# --- Introspection helpers --- #

@pytest.mark.parametrize("ft,scalar,container,children,numeric", [
    (FieldType.STRING,  True,  False, False, False),
    (FieldType.NUMBER,  True,  False, False, True),
    (FieldType.BOOLEAN, True,  False, False, False),
    (FieldType.ENUM,    True,  False, False, False),
    (FieldType.LIST,    False, True,  True,  False),
    (FieldType.DICT,    False, True,  True,  False),
    (FieldType.REF,     False, False, False, False),
    (FieldType.INVALID, False, False, False, False),
])
def test_introspection_helpers(ft, scalar, container, children, numeric):
    assert ft.is_scalar() == scalar
    assert ft.is_container() == container
    assert ft.allows_children() == children
    assert ft.is_numeric() == numeric
