#!/usr/bin/env python3
import pytest
from pydantic import ValidationError

from procdocs.core.document.metadata import DocumentMetadata
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
def test_document_type_normalization_and_lowercasing(raw, expected):
    md = DocumentMetadata(document_type=raw)
    assert md.document_type == expected


def test_document_version_trimmed_when_present():
    md = DocumentMetadata(document_type="test", document_version="  0.3  ")
    assert md.document_version == "0.3"


def test_document_version_none_when_blank_or_missing():
    assert DocumentMetadata(document_type="test").document_version is None
    assert DocumentMetadata(document_type="test", document_version="   ").document_version is None


def test_inherits_default_format_version():
    md = DocumentMetadata(document_type="test")
    assert md.format_version == BaseMetadata.current_format_version()


# --- Invalid construction --- #

@pytest.mark.parametrize("bad", [None, "", "   "])
def test_invalid_empty_document_type_raises(bad):
    with pytest.raises(ValidationError, match="Invalid name: must be a non-empty string"):
        DocumentMetadata(document_type=bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", ["bad name", "inv@lid", "slash/name", "star*name"])
def test_invalid_document_type_chars_raises(bad):
    with pytest.raises(ValidationError, match="Allowed pattern"):
        DocumentMetadata(document_type=bad)


def test_top_level_extra_forbidden():
    with pytest.raises(ValidationError, match=r"extra_forbidden|Extra inputs are not permitted"):
        DocumentMetadata(document_type="test", custom="nope")  # type: ignore[arg-type]


def test_extensions_allowed_via_base():
    md = DocumentMetadata(document_type="test", extensions={"author": "alice"})
    assert md.extensions["author"] == "alice"


# --- Assignment validation --- #

def test_assignment_normalizes_and_validates_document_type():
    md = DocumentMetadata(document_type="test")
    md.document_type = "  New-Name  "
    assert md.document_type == "new-name"


def test_assignment_invalid_document_type_raises():
    md = DocumentMetadata(document_type="test")
    with pytest.raises(ValidationError, match="Allowed pattern"):
        md.document_type = "bad name!"


# --- Format version behavior (inherited) --- #

def test_invalid_format_version_from_parent_rules():
    with pytest.raises(ValidationError, match="Invalid format version"):
        DocumentMetadata(document_type="test", format_version="1.2")  # not strict semver


def test_valid_format_version_override():
    md = DocumentMetadata(document_type="test", format_version="1.2.3")
    assert md.format_version == "1.2.3"
