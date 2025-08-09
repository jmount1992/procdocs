#!/usr/bin/env python3

import hashlib
import pytest
from pydantic import ValidationError, ConfigDict, BaseModel

from procdocs.core.schema.field_descriptor import FieldDescriptor
from procdocs.core.schema.field_type import FieldType


# Helper: ensure assignment validation runs, like in your real models
class Dummy(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    fd: FieldDescriptor


# --- Construction: scalars --- #

def test_scalar_minimal_ok():
    fd = FieldDescriptor(fieldname="id")
    assert fd.fieldname == "id"
    assert fd.fieldtype is FieldType.STRING
    assert fd.required is True
    assert isinstance(fd.uid, str) and len(fd.uid) == 10


@pytest.mark.parametrize("bad", [None, "", "   "])
def test_fieldname_missing_or_blank_raises(bad):
    with pytest.raises(ValidationError, match="The 'fieldname' key is not set"):
        FieldDescriptor(fieldname=bad)  # type: ignore[arg-type]


def test_reserved_fieldname_raises(monkeypatch):
    # inject a reserved name for test
    from procdocs.core import constants as C
    monkeypatch.setattr(C, "RESERVED_FIELDNAMES", set(["metadata", "structure", "reserved_test"]))
    with pytest.raises(ValidationError, match="reserved name"):
        FieldDescriptor(fieldname="reserved_test")


def test_fieldname_pattern_violation_raises():
    bad = "bad name"
    import re
    from procdocs.core.constants import FIELDNAME_ALLOWED_PATTERN
    expected = re.escape(f"must match the pattern '{FIELDNAME_ALLOWED_PATTERN.pattern}'")
    with pytest.raises(ValidationError, match=expected):
        FieldDescriptor(fieldname=bad)


@pytest.mark.parametrize("raw,ok", [
    ("string", True),
    ("enum", True),
    ("list", True),
    ("dict", True),
    ("number", True),
    ("boolean", True),
    ("nope", False),
])
def test_fieldtype_parse_and_invalid(raw, ok):
    if ok:
        if raw == "enum":
            fd = FieldDescriptor(fieldname="x", fieldtype=raw, options=["a", "b"])
        else:
            fd = FieldDescriptor(fieldname="x", fieldtype=raw)
        assert fd.fieldtype is FieldType.parse(raw)
    else:
        with pytest.raises(ValidationError, match="Unknown fieldtype"):
            FieldDescriptor(fieldname="x", fieldtype=raw)


# --- Regex pattern validation --- #
def test_valid_regex_pattern_is_accepted():
    # Ensures the 'pattern' validator covers the non-error branch
    fd = FieldDescriptor(fieldname="code", pattern=r"^\d+$")
    assert fd.pattern == r"^\d+$"


def test_invalid_regex_pattern_raises():
    with pytest.raises(ValidationError, match="Invalid regex pattern"):
        FieldDescriptor(fieldname="code", pattern="(")  # unbalanced


# --- ENUM rules --- #

def test_enum_requires_non_empty_unique_options():
    with pytest.raises(ValidationError, match="must define 'options'"):
        FieldDescriptor(fieldname="status", fieldtype="enum")
    with pytest.raises(ValidationError, match="duplicates"):
        FieldDescriptor(fieldname="status", fieldtype="enum", options=["a", "a"])
    with pytest.raises(ValidationError, match="must not contain empty"):
        FieldDescriptor(fieldname="status", fieldtype="enum", options=["", "ok"])
    fd = FieldDescriptor(fieldname="status", fieldtype="enum", options=["ok", "fail"])
    assert fd.options == ["ok", "fail"]


# --- Children rules --- #

def test_children_only_allowed_for_list_or_dict():
    with pytest.raises(ValidationError, match="only allowed for 'list' or 'dict'"):
        FieldDescriptor(fieldname="x", fieldtype="string", fields=[FieldDescriptor(fieldname="y")])


def test_list_must_have_exactly_one_child_when_provided():
    # zero children when provided
    with pytest.raises(ValidationError, match="at least one child"):
        FieldDescriptor(fieldname="items", fieldtype="list", fields=[])

    # exactly one child is OK
    fd = FieldDescriptor(fieldname="items", fieldtype="list", fields=[FieldDescriptor(fieldname="element")])
    assert fd.is_list() and fd.fields and len(fd.fields) == 1


def test_dict_may_have_children_and_not_empty_when_provided():
    with pytest.raises(ValidationError, match="at least one child"):
        FieldDescriptor(fieldname="cfg", fieldtype="dict", fields=[])
    fd = FieldDescriptor(fieldname="cfg", fieldtype="dict", fields=[FieldDescriptor(fieldname="k")])
    assert fd.is_dict() and fd.fields and len(fd.fields) == 1


def test_list_with_multiple_child_fields_allowed():
    """LIST type can define multiple child fields when describing dict-like elements."""
    fd = FieldDescriptor(
        fieldname="steps",
        fieldtype="list",
        fields=[
            FieldDescriptor(fieldname="step_number", fieldtype="number"),
            FieldDescriptor(fieldname="action", fieldtype="string"),
            FieldDescriptor(fieldname="notes", fieldtype="string", required=False)
        ]
    )

    assert fd.is_list()
    assert fd.fieldtype == FieldType.LIST
    assert len(fd.fields) == 3
    # Child fields should be FieldDescriptor instances
    for child in fd.fields:
        assert isinstance(child, FieldDescriptor)


# --- Assignment validation via wrapper model --- #

def test_assignment_fieldname_is_normalized_and_validated():
    w = Dummy(fd=FieldDescriptor(fieldname="ok"))
    with pytest.raises(ValidationError, match="must match the pattern"):
        w.fd.fieldname = "bad name"
    w.fd.fieldname = "  good_name  "
    assert w.fd.fieldname == "good_name"


def test_options_assignment_revalidated():
    w = Dummy(fd=FieldDescriptor(fieldname="status", fieldtype="enum", options=["ok"]))
    with pytest.raises(ValidationError, match="duplicates"):
        w.fd.options = ["a", "a"]


# --- Helper methods coverage --- #
def test_is_fieldtype_helper_accepts_str_and_enum_member():
    fd = FieldDescriptor(fieldname="qty", fieldtype="number")
    assert fd.is_fieldtype("number")
    assert fd.is_fieldtype(FieldType.NUMBER)
    assert not fd.is_fieldtype("string", FieldType.BOOLEAN)

def test_is_enum_helper_true_and_false():
    e = FieldDescriptor(fieldname="status", fieldtype="enum", options=["ok", "fail"])
    s = FieldDescriptor(fieldname="name", fieldtype="string")
    assert e.is_enum() is True
    assert s.is_enum() is False


# --- UID path-based branch --- #
def test_uid_uses_path_when_set():
    fd = FieldDescriptor(fieldname="id")
    uid_fallback = fd.uid  # based on (fieldname, nesting_level)

    # Simulate DocumentSchema assigning canonical path
    fd._path = "root/section/id"  # PrivateAttr is a normal attribute at runtime
    expected = hashlib.sha1("root/section/id".encode("utf-8")).hexdigest()[:10]

    assert fd.uid != uid_fallback
    assert fd.uid == expected
