#!/usr/bin/env python3
import json
import hashlib
import pytest
from pathlib import Path

from procdocs.core.constants import DEFAULT_TEXT_ENCODING
from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.schema.field_descriptor import FieldDescriptor


# --- Helpers --- #

def _sha10(s: str) -> str:
    return hashlib.sha256(s.encode(DEFAULT_TEXT_ENCODING)).hexdigest()[:10]


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
                "item": {"fieldname": "element"},
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
    # dict child path
    assert f1.spec.fields[0]._path == "group/child"   # type: ignore[attr-defined]
    assert f2._path == "items"
    # list item path uses the [] segment for UID stability
    assert f2.spec.item._path == "items[]/element"    # type: ignore[attr-defined]

    # uid is sha256 of canonical path
    assert f0.uid == _sha10("id")
    assert f1.spec.fields[0].uid == _sha10("group/child")   # type: ignore[attr-defined]
    assert f2.spec.item.uid == _sha10("items[]/element")    # type: ignore[attr-defined]


def test_from_file_non_json_extension_rejected(tmp_path):
    p = tmp_path / "schema.yaml"
    p.write_text("{}", encoding=DEFAULT_TEXT_ENCODING)
    with pytest.raises(ValueError, match="Invalid schema file extension for"):
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
            FieldDescriptor(  # type: ignore[arg-type]
                fieldname="parent",
                fieldtype="dict",
                # provide spec via flat authoring using 'fields'
                fields=[{"fieldname": "child"}],
            ),
        ]
    })
    assert ds.structure[0]._path == "root"
    # dict child path
    assert ds.structure[1].spec.fields[0]._path == "parent/child"  # type: ignore[attr-defined]



def test_duplicate_fieldnames_in_list_item_dict_raises():
    """
    Covers the LIST branch of _check_no_duplicates():
      structure.items[] -> item is DICT -> duplicate among item.spec.fields
    """
    payload = {
        "metadata": {"schema_name": "x"},
        "structure": [
            {
                "fieldname": "items",
                "fieldtype": "list",
                "item": {
                    "fieldname": "row",
                    "fieldtype": "dict",
                    "fields": [
                        {"fieldname": "a"},
                        {"fieldname": "a"},   # duplicate inside the dict held by the list item
                    ],
                },
            }
        ],
    }
    with pytest.raises(ValueError, match=r"Duplicate field names at 'structure\.items\[\]\.row'"):
        DocumentSchema.model_validate(payload)


def test_assign_paths_nested_under_list_of_dict():
    """
    Happy path: LIST whose item is a DICT with unique children.
    Ensures _assign_paths sets canonical paths for nested children beneath '[]'.
    """
    payload = {
        "metadata": {"schema_name": "ok"},
        "structure": [
            {
                "fieldname": "items",
                "fieldtype": "list",
                "item": {
                    "fieldname": "row",
                    "fieldtype": "dict",
                    "fields": [
                        {"fieldname": "a"},
                        {"fieldname": "b"},
                    ],
                },
            }
        ],
    }
    ds = DocumentSchema.model_validate(payload)
    item = ds.structure[0]
    # item path
    assert item._path == "items"
    # list element path uses '[]', and dict children extend from that
    assert item.spec.item._path == "items[]/row"          # type: ignore[attr-defined]
    child_paths = [fd._path for fd in item.spec.item.spec.fields]  # type: ignore[attr-defined]
    assert child_paths == ["items[]/row/a", "items[]/row/b"]


def test_from_file_accepts_uppercase_json_extension(tmp_path: Path):
    payload = {
        "metadata": {"schema_name": "Demo"},
        "structure": [{"fieldname": "id"}],
    }
    p = tmp_path / "schema.JSON"  # uppercase
    p.write_text(json.dumps(payload), encoding=DEFAULT_TEXT_ENCODING)
    ds = DocumentSchema.from_file(p)
    assert ds.schema_name == "demo"