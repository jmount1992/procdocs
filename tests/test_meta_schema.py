#!/usr/bin/env python3

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from procdocs.core.document_schema import DocumentSchema


# --- Helpers --- #
def make_field(fieldname, fieldtype=None, fields=None):
    d = {"fieldname": fieldname}
    if fieldtype:
        d["fieldtype"] = fieldtype
    if fields:
        d["fields"] = fields
    return d


# --- Basic Construction --- #
def test_valid_meta_schema_from_dict():
    data = {
        "metadata": {
            "schema_name": "wi",
            "format_version": "0.0.0"
        },
        "structure": [
            make_field("id"),
            make_field("title")
        ]
    }
    ms = DocumentSchema.from_dict(data)
    assert ms.metadata.document_type == "wi"
    assert len(ms.structure) == 2
    assert ms.structure[0].fieldname == "id"
    assert ms.structure[1].fieldname == "title"


def test_missing_required_metadata_fields():
    data = {
        "metadata": {
            "schema_name": "wi"  # missing format_version
        },
        "structure": [make_field("id")]
    }
    with pytest.raises(ValueError, match="format_version"):
        DocumentSchema.from_dict(data, strict=True)


# --- Structure Validation --- #
def test_duplicate_fields_same_level_raise():
    data = {
        "metadata": {
            "schema_name": "wi",
            "format_version": "0.0.0"
        },
        "structure": [
            make_field("id"),
            make_field("id")
        ]
    }
    with pytest.raises(ValueError, match="Duplicate field names"):
        DocumentSchema.from_dict(data, strict=True)


def test_duplicate_fields_nested_level_raise():
    data = {
        "metadata": {
            "schema_name": "wi",
            "format_version": "0.0.0"
        },
        "structure": [
            make_field("steps", fieldtype="list", fields=[
                make_field("title"),
                make_field("title")  # Duplicate within same nested level
            ])
        ]
    }
    with pytest.raises(ValueError, match="Duplicate field names"):
        DocumentSchema.from_dict(data, strict=True)


def test_duplicate_fields_allowed_between_levels():
    data = {
        "metadata": {
            "schema_name": "wi",
            "format_version": "0.0.0"
        },
        "structure": [
            make_field("title"),
            make_field("steps", fieldtype="list", fields=[
                make_field("title")  # Same name, different level
            ])
        ]
    }
    ms = DocumentSchema.from_dict(data, strict=True)
    assert ms.structure[0].fieldname == "title"
    assert ms.structure[1].fieldname == "steps"
    assert ms.structure[1].fields[0].fieldname == "title"


# --- File Loading --- #
def test_valid_meta_schema_from_file():
    data = {
        "metadata": {
            "schema_name": "wi",
            "format_version": "0.0.0"
        },
        "structure": [
            make_field("id")
        ]
    }
    with TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "schema.json"
        with open(filepath, "w") as f:
            json.dump(data, f)

        ms = DocumentSchema.from_file(filepath, strict=True)
        assert ms.structure[0].fieldname == "id"


def test_from_file_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        DocumentSchema.from_file(Path("nonexistent.json"))


def test_from_file_invalid_type_raises():
    with pytest.raises(TypeError):
        DocumentSchema.from_file(123)  # Not str or Path
