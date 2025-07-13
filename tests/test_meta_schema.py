#!/usr/bin/env python3

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from procdocs.core.meta_schema import MetaSchema  # Adjust as needed
from procdocs.core.field_descriptor import FieldDescriptor  # Adjust as needed


# --- Helpers --- #
def make_field(fieldname, fieldtype=None, fields=None):
    d = {"field": fieldname}
    if fieldtype:
        d["fieldtype"] = fieldtype
    if fields:
        d["fields"] = fields
    return d


# --- Basic Construction --- #
def test_valid_meta_schema_from_dict():
    data = {
        "metadata": {
            "filetype": "wi",
            "meta_schema_version": "0.1"
        },
        "structure": [
            make_field("id"),
            make_field("title")
        ]
    }
    ms = MetaSchema.from_dict(data)
    assert ms.metadata["filetype"] == "wi"
    assert len(ms.structure) == 2
    assert ms.structure[0].fieldname == "id"
    assert ms.structure[1].fieldname == "title"


def test_missing_required_metadata_fields():
    data = {
        "metadata": {
            "filetype": "wi"  # missing meta_schema_version
        },
        "structure": [make_field("id")]
    }
    with pytest.raises(ValueError, match="meta_schema_version"):
        MetaSchema.from_dict(data, strict=True)


# --- Structure Validation --- #
def test_duplicate_fields_same_level_raise():
    data = {
        "metadata": {
            "filetype": "wi",
            "meta_schema_version": "0.1"
        },
        "structure": [
            make_field("id"),
            make_field("id")
        ]
    }
    with pytest.raises(ValueError, match="Duplicate field names"):
        MetaSchema.from_dict(data, strict=True)


def test_duplicate_fields_nested_level_raise():
    data = {
        "metadata": {
            "filetype": "wi",
            "meta_schema_version": "0.1"
        },
        "structure": [
            make_field("steps", fieldtype="list", fields=[
                make_field("title"),
                make_field("title")  # Duplicate within same nested level
            ])
        ]
    }
    with pytest.raises(ValueError, match="Duplicate field names"):
        MetaSchema.from_dict(data, strict=True)


def test_duplicate_fields_allowed_between_levels():
    data = {
        "metadata": {
            "filetype": "wi",
            "meta_schema_version": "0.1"
        },
        "structure": [
            make_field("title"),
            make_field("steps", fieldtype="list", fields=[
                make_field("title")  # Same name, different level
            ])
        ]
    }
    ms = MetaSchema.from_dict(data, strict=True)
    assert ms.structure[0].fieldname == "title"
    assert ms.structure[1].fieldname == "steps"
    assert ms.structure[1].fields[0].fieldname == "title"


# --- File Loading --- #
def test_valid_meta_schema_from_file():
    data = {
        "metadata": {
            "filetype": "wi",
            "meta_schema_version": "0.1"
        },
        "structure": [
            make_field("id")
        ]
    }
    with TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "schema.json"
        with open(filepath, "w") as f:
            json.dump(data, f)

        ms = MetaSchema.from_file(filepath, strict=True)
        assert ms.structure[0].fieldname == "id"


def test_from_file_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        MetaSchema.from_file(Path("nonexistent.json"))


def test_from_file_invalid_type_raises():
    with pytest.raises(TypeError):
        MetaSchema.from_file(123)  # Not str or Path
