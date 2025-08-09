#!/usr/bin/env python3
import json
import hashlib
import pytest

from procdocs.core.constants import DEFAULT_TEXT_ENCODING
from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.schema.field_descriptor import FieldDescriptor


# --- Helpers --- #

def _sha10(s: str) -> str:
    return hashlib.sha1(s.encode(DEFAULT_TEXT_ENCODING)).hexdigest()[:10]


# --- from_file (JSON-only) --- #

def test_from_file_json_only_success(tmp_path):
    schema = {
        "metadata": {"schema_name": "Test"},  # format_version defaults via BaseMetadata
        "structure": [
            {"fieldname": "id"},
            {
                "fieldname": "group",
                "fieldtype": "dict",
                "fields": [
                    {"fieldname": "child"},
                ],
            },
            {
                "fieldname": "items",
                "fieldtype": "list",
                "fields": [{"fieldname": "element"}],
            },
        ],
    }
    p = tmp_path / "schema.json"
    p.write_text(json.dumps(schema), encoding=DEFAULT_TEXT_ENCODING)

    ds = DocumentSchema.from_file(p)

    # convenience props pull from metadata
    assert ds.schema_name == "test"          # normalized to lowercase by SchemaMetadata
    assert isinstance(ds.format_version, str)

    # canonical paths assigned
    f0, f1, f2 = ds.structure
    assert f0._path == "id"
    assert f1._path == "group"
    assert f1.fields[0]._path == "group/child"
    assert f2._path == "items"
    assert f2.fields[0]._path == "items/element"

    # uid is sha1 of canonical path
    assert f0.uid == _sha10("id")
    assert f1.fields[0].uid == _sha10("group/child")
    assert f2.fields[0].uid == _sha10("items/element")


def test_from_file_non_json_extension_rejected(tmp_path):
    p = tmp_path / "schema.yaml"
    p.write_text("{}", encoding=DEFAULT_TEXT_ENCODING)
    with pytest.raises(ValueError, match=r"expected a \.json file"):
        DocumentSchema.from_file(p)


def test_from_file_missing_file_raises(tmp_path):
    p = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError, match="does not exist"):
        DocumentSchema.from_file(p)


# --- Duplicate detection --- #

def test_duplicate_fieldnames_top_level_raises():
    payload = {
        "metadata": {"schema_name": "x"},
        "structure": [
            {"fieldname": "id"},
            {"fieldname": "id"},
        ],
    }
    with pytest.raises(ValueError, match=r"Duplicate field names at 'structure'"):
        DocumentSchema.model_validate(payload)


def test_duplicate_fieldnames_nested_raises():
    payload = {
        "metadata": {"schema_name": "x"},
        "structure": [
            {
                "fieldname": "group",
                "fieldtype": "dict",
                "fields": [
                    {"fieldname": "a"},
                    {"fieldname": "a"},
                ],
            }
        ],
    }
    with pytest.raises(ValueError, match=r"Duplicate field names at 'structure\.group'"):
        DocumentSchema.model_validate(payload)


# --- model_validate_json path --- #

def test_model_validate_json_allows_in_memory_json():
    payload = {
        "metadata": {"schema_name": "Demo"},
        "structure": [{"fieldname": "title"}],
    }
    ds = DocumentSchema.model_validate_json(json.dumps(payload))
    assert ds.schema_name == "demo"
    assert ds.structure[0]._path == "title"
    assert ds.structure[0].uid == _sha10("title")


# --- Empty structure --- #

def test_empty_structure_is_allowed():
    ds = DocumentSchema.model_validate({"metadata": {"schema_name": "empty"}, "structure": []})
    assert isinstance(ds, DocumentSchema)
    assert ds.structure == []


# --- Integration with FieldDescriptor instances (optional sanity) --- #

def test_assignment_into_existing_fielddescriptor_respects_path():
    # Build with FieldDescriptor instances directly (not just dicts)
    ds = DocumentSchema.model_validate({
        "metadata": {"schema_name": "pathcheck"},
        "structure": [
            FieldDescriptor(fieldname="root"),  # type: ignore[arg-type]
            FieldDescriptor(fieldname="parent", fieldtype="dict", fields=[  # type: ignore[arg-type]
                FieldDescriptor(fieldname="child")  # type: ignore[arg-type]
            ])
        ]
    })
    assert ds.structure[0]._path == "root"
    assert ds.structure[1].fields[0]._path == "parent/child"
