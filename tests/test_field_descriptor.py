#!/usr/bin/env python3

import pytest
from procdocs.engine.field_descriptor import FieldDescriptor, FieldType, RESERVED_FIELDS


# --- Field Name Validation --- #

def test_valid_fieldname():
    desc = FieldDescriptor({"field": "name"})
    assert desc.field == "name"


@pytest.mark.parametrize("fieldname", list(RESERVED_FIELDS))
def test_reserved_fieldname_raises(fieldname):
    with pytest.raises(ValueError, match="is a reserved name"):
        FieldDescriptor({"field": fieldname, "fieldtype": "string"})


def test_unset_fieldname():
    with pytest.raises(ValueError, match="'field' key is not set"):
        FieldDescriptor({})


# --- FieldType Handling --- #

@pytest.mark.parametrize("ft_str, ft_enum", [
    ("string", FieldType.STRING),
    ("number", FieldType.NUMBER),
    ("boolean", FieldType.BOOLEAN),
    ("list", FieldType.LIST),
    ("dict", FieldType.DICT),
    ("enum", FieldType.ENUM),
])
def test_valid_fieldtypes_str(ft_str, ft_enum):
    desc = FieldDescriptor({"field": "name", "fieldtype": ft_str})
    assert isinstance(desc.fieldtype, FieldType)
    assert desc.fieldtype == ft_enum


@pytest.mark.parametrize("ft_enum", list(FieldType))
def test_valid_fieldtypes_enum(ft_enum):
    desc = FieldDescriptor({"field": "name", "fieldtype": ft_enum})
    assert isinstance(desc.fieldtype, FieldType)
    assert desc.fieldtype == ft_enum


def test_invalid_fieldtypes():
    with pytest.raises(ValueError, match="Invalid fieldtype"):
        FieldDescriptor({"field": "name", "fieldtype": "invalid"})


def test_fieldtype_defaults_to_string():
    desc = FieldDescriptor({"field": "undecided"})
    assert desc.fieldtype == FieldType.STRING


def test_get_fieldtype_non_strict_returns_none():
    desc = FieldDescriptor({"field": "whatever", "fieldtype": "string"})  # to avoid validation error
    result = desc._get_fieldtype("invalid_type", strict=False)
    assert result is None


# --- Required, Default, Options, Description --- #

def test_default_and_description_and_options_are_stored():
    desc = FieldDescriptor({
        "field": "sensor",
        "fieldtype": "string",
        "default": "imu",
        "description": "Type of sensor",
        "options": ["imu", "gps"]
    })
    assert desc.default == "imu"
    assert desc.description == "Type of sensor"
    assert desc.options == ["imu", "gps"]


@pytest.mark.parametrize("required", [True, False])
def test_required_field_parsing(required):
    desc = FieldDescriptor({"field": "active", "fieldtype": "boolean", "required": required})
    assert desc.required is required


def test_required_field_invalid_type():
    with pytest.raises(ValueError, match="must be boolean"):
        FieldDescriptor({"field": "active", "fieldtype": "boolean", "required": "yes"})


# --- Regex Pattern Validation --- #

def test_valid_regex_pattern_is_accepted():
    desc = FieldDescriptor({
        "field": "serial",
        "fieldtype": "string",
        "pattern": r"^[A-Z]{3}-\d{4}$"
    })
    assert desc.pattern == r"^[A-Z]{3}-\d{4}$"


def test_invalid_regex_pattern_raises():
    with pytest.raises(ValueError, match=r"Invalid regex pattern '.*unterminated character set.*'"):
        FieldDescriptor({
            "field": "broken",
            "fieldtype": "string",
            "pattern": "[a-z"
        })


# --- Nested Fields Validation --- #

def test_list_with_nested_fields():
    desc = FieldDescriptor({
        "field": "items",
        "fieldtype": "list",
        "fields": [
            {"field": "value", "fieldtype": "number"}
        ]
    })
    assert desc.fieldtype == FieldType.LIST
    assert len(desc.fields) == 1
    assert isinstance(desc.fields[0], FieldDescriptor)
    assert desc.fields[0].field == "value"


def test_dict_with_nested_fields():
    desc = FieldDescriptor({
        "field": "params",
        "fieldtype": "dict",
        "fields": [
            {"field": "threshold", "fieldtype": "number"}
        ]
    })
    assert desc.fieldtype == FieldType.DICT
    assert len(desc.fields) == 1
    assert desc.fields[0].field == "threshold"


@pytest.mark.parametrize("ftype", ["string", "number", "boolean", "enum"])
def test_scalar_fieldtypes_reject_nested_fields(ftype):
    with pytest.raises(ValueError, match="Nested 'fields' only allowed for 'list' or 'dict' types"):
        FieldDescriptor({
            "field": "bad_scalar",
            "fieldtype": ftype,
            "fields": [{"field": "oops", "fieldtype": "string"}]
        })


# --- is_fieldtype() Behavior --- #

@pytest.mark.parametrize("value, expected", [
    ("string", FieldType.STRING),
    ("number", FieldType.NUMBER),
    ("boolean", FieldType.BOOLEAN),
    ("list", FieldType.LIST),
    ("dict", FieldType.DICT),
    ("enum", FieldType.ENUM),
])
def test_is_fieldtype(value, expected):
    not_fields = [ft for ft in FieldType if ft != expected]

    desc = FieldDescriptor({"field": "name", "fieldtype": value})
    assert desc.fieldtype == expected
    assert desc.is_fieldtype(expected) is True
    assert desc.is_fieldtype(str(expected.value)) is True  # also test string variant
    assert desc.is_fieldtype(list(FieldType)) is True       # test list variant

    for fieldtype in not_fields:
        assert desc.is_fieldtype(fieldtype) is False


def test_is_fieldtype_with_tuple_and_list_variants():
    desc = FieldDescriptor({"field": "mode", "fieldtype": "enum"})
    assert desc.is_fieldtype(("string", "enum")) is True
    assert desc.is_fieldtype(["number", "dict"]) is False


# -- Repr --- #

def test_repr_contains_field_type_and_index():
    desc = FieldDescriptor({"field": "depth", "fieldtype": "number"})
    rep = repr(desc)
    assert "depth" in rep
    assert "index=0" in rep
    assert "FieldType.NUMBER" in rep
