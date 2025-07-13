#!/usr/bin/env python3

import pytest

from procdocs.core.base_metadata import BaseMetadata


# --- Minimal subclass for testing ---
class SampleMetadata(BaseMetadata):
    def __init__(self):
        super().__init__()

    def _required(self):
        return ("format_version", "document_type")


# --- Test cases ---
def test_valid_metadata_assignment():
    md = SampleMetadata()
    md.document_type = "test"
    md.format_version = "1.2.3"
    assert md.document_type == "test"
    assert md.format_version == "1.2.3"


def test_invalid_format_version():
    md = SampleMetadata()
    with pytest.raises(ValueError):
        md.format_version = "1.0"  # Not strict SemVer


def test_missing_required_field_validation():
    md = SampleMetadata()
    md.format_version = "1.0.0"
    with pytest.raises(ValueError, match="Missing required metadata field: 'document_type'"):
        md.validate()


def test_from_dict_known_and_user_fields():
    data = {
        "document_type": "unit_test",
        "format_version": "1.0.0",
        "author": "Alice",
        "priority": "high"
    }
    md = SampleMetadata.from_dict(data)
    assert md.document_type == "unit_test"
    assert md.format_version == "1.0.0"
    assert md.author == "Alice"
    assert md.priority == "high"
    assert md.to_dict()["author"] == "Alice"
    assert md.to_dict()["priority"] == "high"


def test_to_dict_only_shows_fields():
    md = SampleMetadata()
    md.format_version = "1.0.0"
    md._add_user_field("extra", "custom")
    d = md.to_dict()
    assert d["format_version"] == "1.0.0"
    assert d["extra"] == "custom"


def test_unknown_attribute_raises():
    md = SampleMetadata()
    with pytest.raises(AttributeError):
        _ = md.unknown_field