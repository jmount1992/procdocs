#!/usr/bin/env python3

import pytest

from types import SimpleNamespace
from typing import Any
from pydantic import ValidationError

from procdocs.core.runtime_model import build_contents_adapter, _py_type_for
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
                "fields": [
                    {"fieldname": "step_number", "fieldtype": "number"},
                    {"fieldname": "action"},
                ],
            },
        ],
    }
    return DocumentSchema.model_validate(payload)


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

    # in test_adapter_rejects_unknown_keys_any_level
    with pytest.raises(ValidationError, match=r"extra|Extra inputs are not permitted"):
        adapter.validate_python({"id": "AB-123", "title": "t", "priority": "low", "meta": {"owner": "a"}, "steps": [], "oops": 1})

    with pytest.raises(ValidationError, match=r"extra|Extra inputs are not permitted"):
        adapter.validate_python({"id": "AB-123", "title": "t", "priority": "low", "meta": {"owner": "a", "x": 1}, "steps": []})


def test_adapter_supports_scalar_list_when_no_element_fields():
    payload = {
        "metadata": {"schema_name": "scalarlist"},
        "structure": [
            {"fieldname": "tags", "fieldtype": "list"}  # no fields => list[str]
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
        fields=None,
        pattern=None,
        options=None,
        fieldname="x",
    )
    t = _py_type_for(fake_fd)  # type: ignore[arg-type]
    # There's no isinstance check for typing.Any; compare its repr
    assert str(t) == str(Any)
