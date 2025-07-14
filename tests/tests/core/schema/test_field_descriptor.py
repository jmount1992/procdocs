#!/usr/bin/env python3

import pytest

from procdocs.core.utils import RESERVED_FIELDNAMES
from procdocs.core.schema.field_descriptor import FieldDescriptor, FieldType


# --- Object Instantiation -- #
def test_object_instantiation():
    fd = FieldDescriptor()
    assert fd.fieldname == None
    assert fd.fieldtype == None
    assert fd.required == None
    assert fd.description == None
    assert fd.options == None
    assert fd.pattern == None
    assert fd.default == None
    assert fd.fields == []
    assert fd.uid == None


# --- Test Field Type Handling --- #
@pytest.mark.parametrize("ft_input, expected_enum, extra", [
    ("string", FieldType.STRING, {}),
    (FieldType.STRING, FieldType.STRING, {}),
    ("number", FieldType.NUMBER, {}),
    (FieldType.NUMBER, FieldType.NUMBER, {}),
    ("boolean", FieldType.BOOLEAN, {}),
    (FieldType.BOOLEAN, FieldType.BOOLEAN, {}),
    ("list", FieldType.LIST, {}),
    (FieldType.LIST, FieldType.LIST, {}),
    ("dict", FieldType.DICT, {}),
    (FieldType.DICT, FieldType.DICT, {}),
    ("enum", FieldType.ENUM, {"options": ["A", "B"]}),
    (FieldType.ENUM, FieldType.ENUM, {"options": ["A", "B"]}),
])
def test_fieldtype_and_type_check_helpers(ft_input, expected_enum, extra):
    data = {"fieldname": "name", "fieldtype": ft_input, **extra}
    desc = FieldDescriptor.from_dict(data)
    assert desc.fieldtype == expected_enum

    # Check is_fieldtype behavior
    assert desc.is_fieldtype(expected_enum) is True
    assert desc.is_fieldtype(expected_enum.value) is True
    assert desc.is_fieldtype([expected_enum]) is True

    # Check negative cases
    others = [ft for ft in FieldType if ft != expected_enum and ft != FieldType.INVALID]
    for other in others:
        assert desc.is_fieldtype(other) is False


def test_invalid_fieldtype_is_rejected():
    with pytest.raises(ValueError, match="Invalid fieldtype 'blorp'"):
        FieldDescriptor.from_dict({"fieldname": "name", "fieldtype": "blorp"})


def test_fieldtype_defaults_to_string_if_not_provided():
    desc = FieldDescriptor.from_dict({"fieldname": "undecided"})
    assert desc.fieldtype == FieldType.STRING


def test_is_fieldtype_with_multiple_values():
    desc = FieldDescriptor.from_dict({"fieldname": "setting", "fieldtype": "enum", "options": ["A", "B"]})
    assert desc.is_fieldtype(("enum", "dict")) is True
    assert desc.is_fieldtype(["number", "list"]) is False


@pytest.mark.parametrize("fieldtype, expected", [
    (FieldType.STRING, {"is_list": False, "is_dict": False, "is_enum": False}),
    (FieldType.NUMBER, {"is_list": False, "is_dict": False, "is_enum": False}),
    (FieldType.BOOLEAN, {"is_list": False, "is_dict": False, "is_enum": False}),
    (FieldType.LIST,   {"is_list": True,  "is_dict": False, "is_enum": False}),
    (FieldType.DICT,   {"is_list": False, "is_dict": True,  "is_enum": False}),
    (FieldType.ENUM,   {"is_list": False, "is_dict": False, "is_enum": True}),
])
def test_fieldtype_flags(fieldtype, expected):
    fd = FieldDescriptor()
    fd._fieldtype = fieldtype
    assert fd.is_list() == expected["is_list"]
    assert fd.is_dict() == expected["is_dict"]
    assert fd.is_enum() == expected["is_enum"]


# --- Field Name Validation --- #
def test_valid_fieldname():
    desc = FieldDescriptor.from_dict({"fieldname": "name"})
    assert desc.fieldname == "name"


@pytest.mark.parametrize("fieldname", list(RESERVED_FIELDNAMES))
def test_reserved_fieldname_raises(fieldname):
    with pytest.raises(ValueError, match="is a reserved name"):
        FieldDescriptor.from_dict({"fieldname": fieldname, "fieldtype": "string"})


def test_unset_fieldname_raises():
    with pytest.raises(ValueError, match="'fieldname' key is not set"):
        FieldDescriptor.from_dict({})


# --- FieldType Handling --- #




# --- Required, Default, Options, Description --- #

def test_default_and_description_and_options_are_stored():
    desc = FieldDescriptor.from_dict({
        "fieldname": "sensor",
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
    desc = FieldDescriptor.from_dict({
        "fieldname": "active",
        "fieldtype": "boolean",
        "required": required
    })
    assert desc.required is required


def test_required_field_invalid_type():
    with pytest.raises(ValueError, match="must be boolean"):
        FieldDescriptor.from_dict({"fieldname": "active", "fieldtype": "boolean", "required": "yes"})


# --- Regex Pattern Validation --- #

def test_valid_regex_pattern_is_accepted():
    desc = FieldDescriptor.from_dict({
        "fieldname": "serial",
        "fieldtype": "string",
        "pattern": r"^[A-Z]{3}-\d{4}$"
    })
    assert desc.pattern == r"^[A-Z]{3}-\d{4}$"


def test_invalid_regex_pattern_raises():
    with pytest.raises(ValueError, match=r"Invalid regex pattern '.*unterminated character set.*'"):
        FieldDescriptor.from_dict({
            "fieldname": "broken",
            "fieldtype": "string",
            "pattern": "[a-z"
        })


# --- Nested Fields Validation --- #

def test_list_with_nested_fields():
    desc = FieldDescriptor.from_dict({
        "fieldname": "items",
        "fieldtype": "list",
        "fields": [
            {"fieldname": "value", "fieldtype": "number"}
        ]
    })
    assert desc.is_list()
    assert len(desc.fields) == 1
    assert desc.fields[0].fieldname == "value"
    assert desc.fields[0].fieldtype == FieldType.NUMBER


def test_dict_with_nested_fields():
    desc = FieldDescriptor.from_dict({
        "fieldname": "params",
        "fieldtype": "dict",
        "fields": [
            {"fieldname": "threshold", "fieldtype": "number"}
        ]
    })
    assert desc.is_dict()
    assert len(desc.fields) == 1
    assert desc.fields[0].fieldname == "threshold"
    assert desc.fields[0].fieldtype == FieldType.NUMBER


@pytest.mark.parametrize("ftype", ["string", "number", "boolean", "enum"])
def test_scalar_fieldtypes_reject_nested_fields(ftype):
    with pytest.raises(ValueError, match="Nested 'fields' only allowed for 'list' or 'dict' types"):
        FieldDescriptor.from_dict({
            "fieldname": "bad_scalar",
            "fieldtype": ftype,
            "fields": [{"fieldname": "oops", "fieldtype": "string"}]
        })


def test_enum_field_requires_options():
    with pytest.raises(ValueError, match="ENUM fieldtype must define 'options'"):
        FieldDescriptor.from_dict({
            "fieldname": "mode",
            "fieldtype": "enum"
        })


# --- is_fieldtype() Behavior --- #




# --- UID Generation --- #

def test_uid_is_deterministic_and_unique_by_field_and_level():
    a = FieldDescriptor.from_dict({"fieldname": "depth", "fieldtype": "number"})
    b = FieldDescriptor.from_dict({"fieldname": "depth", "fieldtype": "number"})
    assert a.uid == b.uid  # same level, same name

    c = FieldDescriptor.from_dict({"fieldname": "depth", "fieldtype": "number"}, level=1)
    assert c.uid != a.uid  # different level


# --- __repr__() Behavior --- #

def test_repr_outputs_useful_info():
    desc = FieldDescriptor.from_dict({"fieldname": "depth", "fieldtype": "number", "default": 42})
    rep = repr(desc)
    assert "depth" in rep
    assert "number" in rep
    assert "42" in rep
