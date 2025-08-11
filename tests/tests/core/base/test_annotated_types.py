#!/usr/bin/env python3
import pytest
from pydantic import BaseModel, ValidationError, ConfigDict

from procdocs.core.annotated_types import SchemaName, FreeFormVersion


class _Dummy(BaseModel):
    model_config = ConfigDict(validate_assignment=True)  # <-- add this
    name: SchemaName
    ver: FreeFormVersion = None


# --- SchemaName (normalizer) --- #

@pytest.mark.parametrize("raw,expected", [
    ("test", "test"),
    ("Test", "test"),
    ("  My.Schema_01  ", "my.schema_01"),
    ("A-B_C.D", "a-b_c.d"),
])
def test_schema_name_normalization(raw, expected):
    m = _Dummy(name=raw)
    assert m.name == expected


@pytest.mark.parametrize("bad", [None, "", "   "])
def test_schema_name_empty_raises(bad):
    with pytest.raises(ValidationError, match="Invalid name: must be a non-empty string"):
        _Dummy(name=bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", ["bad name", "inv@lid", "slash/name", "star*name"])
def test_schema_name_invalid_chars_raises(bad):
    with pytest.raises(ValidationError, match="allowed characters"):
        _Dummy(name=bad)


# --- FreeFormVersion (normalizer) --- #

def test_freeform_version_none_remains_none_on_construction():
    m = _Dummy(name="test", ver=None)
    assert m.ver is None


def test_freeform_version_blank_becomes_none_on_construction():
    m = _Dummy(name="test", ver="   ")
    assert m.ver is None


def test_freeform_version_trimmed_on_construction():
    m = _Dummy(name="test", ver="  1.0-draft  ")
    assert m.ver == "1.0-draft"


def test_freeform_version_none_on_assignment():
    m = _Dummy(name="test", ver="x")
    m.ver = None
    assert m.ver is None


def test_freeform_version_blank_becomes_none_on_assignment():
    m = _Dummy(name="test", ver="x")
    m.ver = "   "
    assert m.ver is None


def test_freeform_version_trimmed_on_assignment():
    m = _Dummy(name="test", ver="x")
    m.ver = "  r5  "
    assert m.ver == "r5"
