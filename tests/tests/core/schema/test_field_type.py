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


# --- Coercion via str(value) in parse/try_parse --- #

def test_parse_coerces_via_str_dunder():
    class LooksLikeString:
        def __str__(self):
            return "  ENUM  "   # mixed case + whitespace

    val = LooksLikeString()
    assert FieldType.parse(val) is FieldType.ENUM
    assert FieldType.try_parse(val) is FieldType.ENUM


def test_try_parse_none_returns_none():
    assert FieldType.parse(None) is FieldType.INVALID
    assert FieldType.try_parse(None) is None


# --- Exact identity mapping in from_python_type (not subclass/duck typing) --- #

def test_from_python_type_requires_exact_identity_not_subclass():
    class MyInt(int):
        pass

    class MyList(list):
        pass

    class MyDict(dict):
        pass

    # Exact builtins map to concrete FieldTypes (covered elsewhere),
    # but subclasses should *not* be treated as the same.
    assert FieldType.from_python_type(MyInt) is FieldType.INVALID
    assert FieldType.from_python_type(MyList) is FieldType.INVALID
    assert FieldType.from_python_type(MyDict) is FieldType.INVALID
