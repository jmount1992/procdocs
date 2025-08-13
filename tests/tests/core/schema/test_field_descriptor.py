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
    from procdocs.core.constants import FIELDNAME_ALLOWED_RE
    expected = re.escape(f"must match the pattern '{FIELDNAME_ALLOWED_RE.pattern}'")
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


# --- Defaults injected when spec omitted (major contract) --- #

@pytest.mark.parametrize("raw_type,expected_ft", [
    ("number", FieldType.NUMBER),
    ("boolean", FieldType.BOOLEAN),
    ("ref", FieldType.REF),
])
def test_simple_types_inject_default_spec_when_missing(raw_type, expected_ft):
    fd = FieldDescriptor(fieldname="x", fieldtype=raw_type)
    assert fd.fieldtype is expected_ft
    # Spec exists and matches the type (no error raised)
    assert getattr(fd.spec, "kind", None) == expected_ft.value


# --- Mutual exclusion: flat keys vs spec (authoring safety) --- #

def test_flat_and_spec_together_raises():
    with pytest.raises(ValidationError, match="Provide either flat type-specific keys or 'spec', not both"):
        FieldDescriptor(
            fieldname="x",
            fieldtype="enum",
            options=["a", "b"],                  # flat
            spec={"kind": "enum", "options": ["a", "b"]},  # AND spec
        )


# --- 'spec.kind' must match 'fieldtype' --- #

def test_spec_kind_mismatch_raises():
    with pytest.raises(ValidationError, match=r"'spec\.kind' \(number\) does not match fieldtype 'string'"):
        # Provide explicit spec dict with wrong kind
        FieldDescriptor.model_validate({
            "fieldname": "x",
            "fieldtype": "string",
            "spec": {"kind": "number"},
        })


# --- List sugar & synthesized item fieldname --- #

def test_list_sugar_fields_without_item_is_packed_and_dumps_fields():
    # Author uses 'fields' directly on a list -> should synthesize item=dict(fields=...)
    fd = FieldDescriptor(
        fieldname="rows",
        fieldtype="list",
        fields=[{"fieldname": "a"}, {"fieldname": "b"}],  # flat sugar
    )
    # Internally: item is a dict
    assert fd.spec.item.fieldtype is FieldType.DICT
    dumped = fd.model_dump()
    # Author-friendly dump uses 'fields' only (no 'item')
    assert "fields" in dumped and "item" not in dumped
    assert [f["fieldname"] for f in dumped["fields"]] == ["a", "b"]


def test_list_item_missing_fieldname_is_synthesized_and_hidden_in_dump():
    # Provide an item without fieldname; it should be synthesized from parent fieldname
    fd = FieldDescriptor(
        fieldname="xs",
        fieldtype="list",
        item={"fieldtype": "number"},  # missing fieldname -> synthesize "xs_item"
    )
    # Internal synthesized name exists
    assert fd.spec.item.fieldname == "xs_item"
    # Dump should not expose the synthesized fieldname in 'item'
    dumped = fd.model_dump()
    assert "item" in dumped and "fields" not in dumped
    assert "fieldname" not in dumped["item"]
    assert dumped["item"]["fieldtype"] == "number"


def test_list_of_string_with_pattern_emits_item_not_fields():
    fd = FieldDescriptor(
        fieldname="tags",
        fieldtype="list",
        item={"fieldtype": "string", "pattern": r"^[a-z]+$"},
    )
    dumped = fd.model_dump()
    # Because element is scalar string with a pattern, we emit 'item' (without fieldname)
    assert "item" in dumped and "fields" not in dumped
    assert dumped["item"]["fieldtype"] == "string"
    assert dumped["item"]["pattern"] == r"^[a-z]+$"
    assert "fieldname" not in dumped["item"]


# --- Ref knobs round-trip --- #

def test_ref_knobs_roundtrip_in_dump():
    fd = FieldDescriptor(
        fieldname="path",
        fieldtype="ref",
        cardinality="many",
        allow_globs=True,
        must_exist=True,
        base_dir="/data",
        extensions=[".yml", ".yaml"],
    )
    dumped = fd.model_dump()
    assert dumped["fieldtype"] == "ref"
    assert dumped["cardinality"] == "many"
    assert dumped["allow_globs"] is True
    assert dumped["must_exist"] is True
    assert dumped["base_dir"] == "/data"
    assert dumped["extensions"] == [".yml", ".yaml"]


def test_dict_without_spec_raises_requires_spec_block():
    from pydantic import ValidationError
    from procdocs.core.schema.field_descriptor import FieldDescriptor
    with pytest.raises(ValidationError, match=r"dict requires a 'spec' block"):
        FieldDescriptor(fieldname="cfg", fieldtype="dict")


def test_before_validator_short_circuit_on_non_dict_input():
    from pydantic import ValidationError
    from procdocs.core.schema.field_descriptor import FieldDescriptor
    with pytest.raises(ValidationError, match="valid dictionary"):
        FieldDescriptor.model_validate("not a dict")  # triggers early return path
