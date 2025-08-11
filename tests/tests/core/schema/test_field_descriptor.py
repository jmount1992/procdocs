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
    ("ref", True),
    ("nope", False),
])
def test_fieldtype_parse_and_invalid(raw, ok):
    if ok:
        # supply minimal required per type
        if raw == "enum":
            fd = FieldDescriptor(fieldname="x", fieldtype=raw, options=["a", "b"])  # flat authoring
        elif raw == "list":
            fd = FieldDescriptor(fieldname="x", fieldtype=raw, item={"fieldname": "el"})  # flat item
        elif raw == "dict":
            fd = FieldDescriptor(fieldname="x", fieldtype=raw, fields=[{"fieldname": "k"}])  # flat fields
        else:
            fd = FieldDescriptor(fieldname="x", fieldtype=raw)
        assert fd.fieldtype is FieldType.parse(raw)
    else:
        with pytest.raises(ValidationError, match="Unknown fieldtype"):
            FieldDescriptor(fieldname="x", fieldtype=raw)


# --- String pattern (flat authoring accepted) --- #

def test_string_pattern_flat_is_accepted():
    fd = FieldDescriptor(fieldname="code", pattern=r"^\d+$")
    # pattern is stored inside spec; we don't validate regex here
    d = fd.model_dump()
    assert d["pattern"] == r"^\d+$"


# --- ENUM rules --- #

def test_enum_requires_non_empty_unique_options():
    with pytest.raises(ValidationError, match="requires a 'spec' block|must define 'options'"):
        # enum without options should fail
        FieldDescriptor(fieldname="status", fieldtype="enum")
    with pytest.raises(ValidationError, match="duplicates"):
        FieldDescriptor(fieldname="status", fieldtype="enum", options=["a", "a"])
    with pytest.raises(ValidationError, match="must not contain empty"):
        FieldDescriptor(fieldname="status", fieldtype="enum", options=["", "ok"])
    fd = FieldDescriptor(fieldname="status", fieldtype="enum", options=["ok", "fail"])
    dumped = fd.model_dump()
    assert dumped["options"] == ["ok", "fail"]


# --- Children / nested spec rules --- #

def test_children_keys_not_allowed_for_scalar_types():
    # Providing dict-only key 'fields' on a string type should error
    with pytest.raises(ValidationError, match=r"Unexpected key\(s\) for fieldtype 'string'.*Allowed: \['pattern'\]"):
        FieldDescriptor(fieldname="x", fieldtype="string", fields=[{"fieldname": "y"}])  # type: ignore[arg-type]


def test_list_requires_item():
    fd = FieldDescriptor(fieldname="tags", fieldtype="list")
    dumped = fd.model_dump()
    # Canonical dump for default list[str] has no extra keys
    assert dumped == {"fieldname": "tags", "fieldtype": "list", "required": True}


def test_dict_requires_fields_and_not_empty():
    with pytest.raises(ValidationError):
        # flat fields key present but empty -> DictSpec min_length triggers
        FieldDescriptor(fieldname="cfg", fieldtype="dict", fields=[])
    fd = FieldDescriptor(fieldname="cfg", fieldtype="dict", fields=[{"fieldname": "k"}])
    dumped = fd.model_dump()
    assert dumped["fields"][0]["fieldname"] == "k"


def test_list_of_dict_with_multiple_fields():
    """LIST whose item is a DICT with multiple fields."""
    fd = FieldDescriptor(
        fieldname="steps",
        fieldtype="list",
        item={
            "fieldname": "step",
            "fieldtype": "dict",
            "fields": [
                {"fieldname": "step_number", "fieldtype": "number"},
                {"fieldname": "action", "fieldtype": "string"},
                {"fieldname": "notes", "fieldtype": "string", "required": False},
            ],
        },
    )

    # Internal normalization is still item->dict(...):
    assert fd.spec.item.fieldtype == FieldType.DICT

    dumped = fd.model_dump()

    # Author-friendly dump: 'fields' (no 'item')
    assert dumped["fieldtype"] == "list"
    assert "item" not in dumped
    assert "fields" in dumped and isinstance(dumped["fields"], list)

    names = [f["fieldname"] for f in dumped["fields"]]
    assert names == ["step_number", "action", "notes"]


# --- Assignment validation via wrapper model --- #

def test_assignment_fieldname_is_normalized_and_validated():
    w = Dummy(fd=FieldDescriptor(fieldname="ok"))
    with pytest.raises(ValidationError, match="must match the pattern"):
        w.fd.fieldname = "bad name"
    w.fd.fieldname = "  good_name  "
    assert w.fd.fieldname == "good_name"


# --- UID path-based branch --- #
def test_uid_uses_path_when_set():
    fd = FieldDescriptor(fieldname="id")
    uid_fallback = fd.uid  # based on default path

    # Simulate DocumentSchema assigning canonical path
    fd._path = "root/section/id"  # PrivateAttr is a normal attribute at runtime
    expected = hashlib.sha1("root/section/id".encode("utf-8")).hexdigest()[:10]

    assert fd.uid != uid_fallback
    assert fd.uid == expected
