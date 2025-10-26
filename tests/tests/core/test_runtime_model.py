#!/usr/bin/env python3

import pytest

from types import SimpleNamespace
from typing import Any
from pydantic import ValidationError

from procdocs.core.runtime_model import build_contents_adapter, _py_type_for, _schema_fingerprint
from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.schema.field_type import FieldType


def _make_schema():
    payload = {
        "metadata": {"schema_name": "Test"},
        "structure": [
            {"fieldname": "id", "pattern": r"^[A-Z]{2,4}-\d{3}$"},
            {"fieldname": "title"},
            {"fieldname": "priority", "fieldtype": "enum", "options": ["low", "med", "high"]},
            {
                "fieldname": "meta",
                "fieldtype": "dict",
                "fields": [
                    {"fieldname": "owner"},
                    {"fieldname": "active", "fieldtype": "boolean", "required": False},
                ],
            },
            {
                "fieldname": "steps",
                "fieldtype": "list",
                "item": {
                    "fieldname": "step",
                    "fieldtype": "dict",
                    "fields": [
                        {"fieldname": "step_number", "fieldtype": "number"},
                        {"fieldname": "action"},
                    ],
                },
            },
        ],
    }
    return DocumentSchema.model_validate(payload)


def _schema_with(*, name="Test", structure):
    return DocumentSchema.model_validate({
        "metadata": {"schema_name": name},
        "structure": structure,
    })


# --- Build & reuse adapter --- #

def test_build_contents_adapter_returns_working_adapter():
    schema = _make_schema()
    adapter = build_contents_adapter(schema)

    # Valid contents should round-trip without errors
    contents = {
        "id": "AB-123",
        "title": "Do the thing",
        "priority": "low",
        "meta": {"owner": "alice", "active": True},
        "steps": [{"step_number": 1, "action": "start"}, {"step_number": 2, "action": "finish"}],
    }
    parsed = adapter.validate_python(contents)
    as_dict = adapter.dump_python(parsed)
    assert as_dict["priority"] == "low"
    assert as_dict["steps"][0]["step_number"] == 1.0  # number coerces to float per mapping


def test_build_contents_adapter_is_cached():
    schema = _make_schema()
    a1 = build_contents_adapter(schema)
    a2 = build_contents_adapter(schema)
    assert a1 is a2  # cached instance


# --- Validation errors --- #

def test_adapter_reports_pattern_enum_and_type_errors():
    schema = _make_schema()
    adapter = build_contents_adapter(schema)

    bad = {
        "id": "BAD123",                     # fails pattern
        "title": "x",
        "priority": "urgent",               # not in enum
        "meta": {"owner": "alice", "active": "yes"},  # boolean type
        "steps": [{"step_number": "one", "action": "start"}],  # number type
    }

    with pytest.raises(ValidationError, match=r"id[\s\S]*match"):
        adapter.validate_python(bad)


def test_adapter_rejects_unknown_keys_any_level():
    schema = _make_schema()
    adapter = build_contents_adapter(schema)

    with pytest.raises(ValidationError, match=r"extra|Extra inputs are not permitted"):
        adapter.validate_python({"id": "AB-123", "title": "t", "priority": "low", "meta": {"owner": "a"}, "steps": [], "oops": 1})

    with pytest.raises(ValidationError, match=r"extra|Extra inputs are not permitted"):
        adapter.validate_python({"id": "AB-123", "title": "t", "priority": "low", "meta": {"owner": "a", "x": 1}, "steps": []})


def test_adapter_supports_list_of_strings_when_item_is_string():
    payload = {
        "metadata": {"schema_name": "scalarlist"},
        "structure": [
            {"fieldname": "tags", "fieldtype": "list", "item": {"fieldname": "tag", "fieldtype": "string"}}
        ],
    }
    schema = DocumentSchema.model_validate(payload)
    adapter = build_contents_adapter(schema)

    ok = {"tags": ["a", "b", "c"]}
    parsed = adapter.validate_python(ok)
    as_dict = adapter.dump_python(parsed)
    assert as_dict["tags"] == ["a", "b", "c"]

    with pytest.raises(Exception):
        adapter.validate_python({"tags": [{"x": 1}]})  # dict element not allowed


def test__py_type_for_fallback_any_branch():
    """
    Hit the fallback 'return Any' path by providing a fake descriptor
    with an INVALID fieldtype (which would normally be rejected earlier).
    """
    fake_fd = SimpleNamespace(
        fieldtype=FieldType.INVALID,
        fieldname="x",
        required=True,
        default=None,
        spec=None,
        _path="x",
    )
    t = _py_type_for(fake_fd)  # type: ignore[arg-type]
    # There's no isinstance check for typing.Any; compare its repr
    assert str(t) == str(Any)


# --- REF cardinality mapping (str vs list[str]) --- #

def test_ref_cardinality_one_vs_many():
    schema_one = _schema_with(structure=[{"fieldname": "path", "fieldtype": "ref", "cardinality": "one"}])
    schema_many = _schema_with(structure=[{"fieldname": "paths", "fieldtype": "ref", "cardinality": "many"}])

    a_one = build_contents_adapter(schema_one)
    a_many = build_contents_adapter(schema_many)

    # one -> str accepted; list rejected
    parsed_one = a_one.validate_python({"path": "/tmp/file.txt"})
    dumped_one = a_one.dump_python(parsed_one)
    assert dumped_one["path"] == "/tmp/file.txt"
    with pytest.raises(ValidationError):
        a_one.validate_python({"path": ["/tmp/a", "/tmp/b"]})

    # many -> list[str] accepted; str rejected
    parsed_many = a_many.validate_python({"paths": ["/a", "/b"]})
    dumped_many = a_many.dump_python(parsed_many)
    assert dumped_many["paths"] == ["/a", "/b"]
    with pytest.raises(ValidationError):
        a_many.validate_python({"paths": "/tmp/file.txt"})


# --- Cache key / fingerprint sensitivity --- #

def test_adapter_cache_changes_when_pattern_changes():
    # Same schema name, only the STRING pattern differs → fingerprint must differ
    s1 = _schema_with(structure=[{"fieldname": "id", "pattern": r"^A{2}-\d{3}$"}])
    s2 = _schema_with(structure=[{"fieldname": "id", "pattern": r"^B{2}-\d{3}$"}])

    a1 = build_contents_adapter(s1)
    a2 = build_contents_adapter(s2)
    assert a1 is not a2  # pattern participates in fingerprint


def test_adapter_cache_changes_when_enum_options_change():
    s1 = _schema_with(structure=[{"fieldname": "prio", "fieldtype": "enum", "options": ["low", "med"]}])
    s2 = _schema_with(structure=[{"fieldname": "prio", "fieldtype": "enum", "options": ["low", "med", "high"]}])

    a1 = build_contents_adapter(s1)
    a2 = build_contents_adapter(s2)
    assert a1 is not a2  # options participate in fingerprint


def test_schema_fingerprint_exposes_key_features_for_debugging():
    s = _schema_with(structure=[
        {"fieldname": "id", "pattern": r"^[A-Z]{2}-\d{3}$"},
        {"fieldname": "prio", "fieldtype": "enum", "options": ["low", "med"]},
        {"fieldname": "ref", "fieldtype": "ref", "cardinality": "many"},
    ])
    fp = _schema_fingerprint(s)
    # Contains schema name and format version
    assert s.schema_name in fp and s.format_version in fp
    # Contains canonical path segments and feature markers
    assert "id" in fp and "prio" in fp and "ref" in fp
    assert "pat:" in fp and "opt:low" in fp and "opt:med" in fp and "ref:many" in fp


# --- Required vs optional vs default handling in generated model --- #

def test_required_optional_and_defaults_behavior():
    schema = _schema_with(structure=[
        {"fieldname": "title"},                                       # required string, no default
        {"fieldname": "flag", "fieldtype": "boolean", "required": False},  # optional -> defaults to None
        {"fieldname": "active", "fieldtype": "boolean", "required": False, "default": True},  # optional with default
    ])
    adapter = build_contents_adapter(schema)

    # Missing required field → error
    with pytest.raises(ValidationError):
        adapter.validate_python({})

    # Provide required, leave optionals missing
    parsed = adapter.validate_python({"title": "ok"})
    dumped = adapter.dump_python(parsed)
    # 'flag' becomes None (since field default is None in the model)
    assert "flag" in dumped and dumped["flag"] is None
    # 'active' takes its default True
    assert dumped["active"] is True