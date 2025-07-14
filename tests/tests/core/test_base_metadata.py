#!/usr/bin/env python3

import re
import pytest
from typing import List

from procdocs.core.base_metadata import BaseMetadata


# --- Minimal Subclasses For Testing --- #
class SampleMetadata(BaseMetadata):
    def __init__(self):
        self.document_type = None
        super().__init__()

    @classmethod
    def from_dict(cls, data, strict = True) -> "SampleMetadata":
        return super().from_dict(data, strict)

    def _required(self) -> List[str]:
        return ["format_version", "document_type"]

    def _derived_attributes(self) -> List[str]:
        return ["document_type"]
    

# --- Test Object Instantiation --- #
def test_valid_instantiation():
    md = SampleMetadata()
    assert md.format_version == None
    assert md.document_type == None
    assert md._user_defined == {}


def test_invalid_required_fields_instantiation(monkeypatch):
    def _required(self):
        return ["format_versio", "document_type"]
    monkeypatch.setattr(SampleMetadata, "_required", _required)
    with pytest.raises(AttributeError, match=re.escape("_required() returned invalid attribute")):
        SampleMetadata()


def test_invalid_derived_fields_instantiation(monkeypatch):
    def _derived_attributes(self):
        return ["document_typ"]
    monkeypatch.setattr(SampleMetadata, "_derived_attributes", _derived_attributes)
    with pytest.raises(AttributeError, match=re.escape("_derived_attributes() returned invalid attribute")):
        SampleMetadata()


def test_valid_required_function():
    md = SampleMetadata()
    assert len(md._required()) == 2


def test_valid_derived_attributes_function():
    md = SampleMetadata()
    assert len(md._derived_attributes()) == 1


# --- Test From Dict Data Initialisation --- #
@pytest.mark.parametrize("data", [
    ({"format_version": "0.0.0", "document_type": "test"}),
    ({"format_version": "0.0.0", "document_type": "test", "user_field_1": 1, "user-field-2": "test"})
])
def test_valid_data_strict_initalisation(data):
    md = SampleMetadata.from_dict(data)
    for key, val in data.items():
        assert hasattr(md, key) != None
        assert getattr(md, key) == val


@pytest.mark.parametrize("data,exc_type,match", [
    ({"document_type": "test"}, ValueError, "Missing required metadata fields"),
    ({"format_version": "0.0", "document_type": "test"}, ValueError, "Invalid format version"),
])
@pytest.mark.parametrize("strict", [True, False])
def test_invalid_data_initialisation(data, exc_type, match, strict):
    if strict:
        with pytest.raises(exc_type, match=re.escape(match)):
            SampleMetadata.from_dict(data, strict=True)
    else:
        md = SampleMetadata.from_dict(data, strict=False)
        results = md.validate(strict=False)
        assert any(re.search(re.escape(match), msg) for msg in results.errors), f"Expected error message: {match}"


# --- Other Tests --- #
@pytest.mark.parametrize("version, valid", [
    ("0.0.0", True),
    ("0.0", False),
])
def test_format_version(version, valid):
    md = SampleMetadata()
    if valid:
        md.format_version = version
        assert md.format_version == version
    else:
        with pytest.raises(ValueError, match="Invalid format version"):
            md.format_version = version


def test_user_defined_metadata():
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
    print(md.to_dict())
    assert md.to_dict()["author"] == "Alice"
    assert md.to_dict()["priority"] == "high"


def test_to_dict_only_shows_fields():
    md = SampleMetadata()
    md.format_version = "1.0.0"
    md._add_user_field("extra", "custom")
    d = md.to_dict()
    assert d["format_version"] == "1.0.0"
    assert d["extra"] == "custom"
    assert d["document_type"] == None


def test_unknown_attribute_raises():
    md = SampleMetadata()
    with pytest.raises(AttributeError):
        _ = md.unknown_field

def test_user_field_shadowing_core_fields():
    md = SampleMetadata()
    md.format_version = "1.2.3"
    assert md.format_version == "1.2.3"

    md._add_user_field("format_version", "bogus")
    assert md._user_defined["format_version"] == "bogus"

    assert md.format_version == "1.2.3"
