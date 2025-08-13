#!/usr/bin/env python3
import pytest
from pydantic import ValidationError

from procdocs.core.schema.metadata import SchemaMetadata
from procdocs.core.metadata_base import BaseMetadata


# --- Valid construction --- #

@pytest.mark.parametrize("raw,expected", [
    ("test", "test"),
    ("Test", "test"),
    ("TeST", "test"),
    ("TEST", "test"),
    ("test.schema-01", "test.schema-01"),
    ("  test_schema  ", "test_schema"),
])
def test_schema_name_normalization_and_lowercasing(raw, expected):
    md = SchemaMetadata(schema_name=raw)
    assert md.schema_name == expected


def test_schema_version_trimmed_when_present():
    md = SchemaMetadata(schema_name="test", schema_version="  0.3  ")
    assert md.schema_version == "0.3"


def test_schema_version_none_when_blank_or_missing():
    assert SchemaMetadata(schema_name="test").schema_version is None
    assert SchemaMetadata(schema_name="test", schema_version="   ").schema_version is None


def test_inherits_default_format_version():
    md = SchemaMetadata(schema_name="test")
    assert md.format_version == BaseMetadata.current_format_version()


# --- Invalid construction --- #

@pytest.mark.parametrize("bad_name", [None, "", "   "])
def test_invalid_empty_schema_name_raises(bad_name):
    with pytest.raises(ValidationError, match="Invalid name: must be a non-empty string"):
        SchemaMetadata(schema_name=bad_name)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_name", ["bad name", "inv@lid", "slash/name", "star*name"])
def test_invalid_schema_name_chars_raises(bad_name):
    with pytest.raises(ValidationError, match="Allowed pattern"):
        SchemaMetadata(schema_name=bad_name)


def test_top_level_extra_forbidden():
    with pytest.raises(ValidationError, match=r"extra_forbidden|Extra inputs are not permitted"):
        SchemaMetadata(schema_name="test", custom="nope")  # type: ignore[arg-type]


def test_extensions_allowed_via_base():
    md = SchemaMetadata(schema_name="test", extensions={"owner": "QA"})
    assert md.extensions["owner"] == "QA"


# --- Assignment validation --- #

def test_assignment_normalizes_and_validates_schema_name():
    md = SchemaMetadata(schema_name="test")
    md.schema_name = "  New-Name  "
    assert md.schema_name == "new-name"  # lowercased + trimmed


def test_assignment_invalid_schema_name_raises():
    md = SchemaMetadata(schema_name="test")
    with pytest.raises(ValidationError, match="Allowed pattern"):
        md.schema_name = "bad name!"


# --- Format version behavior (inherited) --- #

def test_invalid_format_version_from_parent_rules():
    with pytest.raises(ValidationError, match="Invalid format version"):
        SchemaMetadata(schema_name="test", format_version="1.2")  # not strict semver


def test_valid_format_version_override():
    md = SchemaMetadata(schema_name="test", format_version="1.2.3")
    assert md.format_version == "1.2.3"


# --- Round-trip stability --- #

def test_round_trip_dump_and_validate_preserves_normalization():
    md = SchemaMetadata(
        schema_name="  Test.Schema-01  ",
        schema_version="  V1-ALPHA  ",
        extensions={" owner ": "qa"},
    )
    dumped = md.model_dump()

    # Normalized in dump
    assert dumped["schema_name"] == "test.schema-01"
    assert dumped["schema_version"] == "V1-ALPHA"
    assert dumped["extensions"] == {"owner": "qa"}

    # Re-validate from dumped dict (serialize -> load)
    md2 = SchemaMetadata.model_validate(dumped)
    assert md2 == md


# --- Assignment semantics for schema_version --- #

def test_schema_version_assignment_trims_and_preserves_case():
    md = SchemaMetadata(schema_name="test")
    md.schema_version = "  V2-Alpha  "
    assert md.schema_version == "V2-Alpha"  # trimmed, case preserved


def test_schema_version_assignment_blank_becomes_none():
    md = SchemaMetadata(schema_name="test", schema_version="x")
    md.schema_version = "   "  # whitespace-only -> None
    assert md.schema_version is None


# --- Validation on update/re-validate path --- #

def test_model_validate_rejects_bad_schema_name():
    payload = {"schema_name": "bad name!"}
    with pytest.raises(ValidationError, match="Allowed pattern"):
        SchemaMetadata.model_validate(payload)