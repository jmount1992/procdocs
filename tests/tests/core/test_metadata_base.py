#!/usr/bin/env python3
import pytest
from pydantic import ValidationError

from procdocs.core.metadata_base import BaseMetadata
from procdocs.core.constants import PROCDOCS_FORMAT_VERSION


# --- Valid construction --- #

@pytest.mark.parametrize("version", ["0.0.1", "1.2.3", "10.0.0"])
def test_construct_with_valid_format_version(version):
    md = BaseMetadata(format_version=version)
    assert md.format_version == version


def test_format_version_normalization_whitespace():
    md = BaseMetadata(format_version="  0.0.1  ")
    assert md.format_version == "0.0.1"


def test_default_format_version_matches_constant():
    md = BaseMetadata()
    assert md.format_version == PROCDOCS_FORMAT_VERSION
    assert BaseMetadata.current_format_version() == PROCDOCS_FORMAT_VERSION


# --- Invalid construction --- #

@pytest.mark.parametrize("bad", ["v1.2.3", "1.2", "1.2.3-alpha", "", None])
def test_construct_with_invalid_format_version_raises(bad):
    with pytest.raises(ValidationError, match="Invalid format version"):
        BaseMetadata(format_version=bad)


# --- Assignment validation --- #

def test_assignment_validation_rejects_invalid_update():
    md = BaseMetadata(format_version="1.2.3")
    with pytest.raises(ValidationError, match="Invalid format version"):
        md.format_version = "1.2"  # not strict semver


def test_assignment_validation_allows_valid_update():
    md = BaseMetadata(format_version="1.2.3")
    md.format_version = "2.0.0"
    assert md.format_version == "2.0.0"


# --- Extra keys vs. extensions --- #

def test_top_level_extra_forbidden():
    with pytest.raises(ValidationError, match=r"extra_forbidden"):
        BaseMetadata(format_version="1.2.3", unexpected="nope")


def test_extensions_accepts_arbitrary_keys():
    md = BaseMetadata(
        format_version="1.2.3",
        extensions={"created_by": "alice@example.com", "reviewed": True},
    )
    assert md.extensions["created_by"] == "alice@example.com"
    assert md.extensions["reviewed"] is True

    # Extensions should be mutable like a normal dict
    md.extensions["ticket"] = "ABC-123"
    assert md.extensions["ticket"] == "ABC-123"


# --- Helper methods (version gating) --- #

@pytest.mark.parametrize(
    "fmt,threshold,expected",
    [
        ("1.2.3", "1.2.3", True),
        ("1.2.3", "1.2.2", True),
        ("1.2.3", "1.3.0", False),
        ("0.0.1", "0.0.2", False),
        ("2.0.0", "1.9.9", True),
    ],
)
def test_format_version_at_least(fmt, threshold, expected):
    md = BaseMetadata(format_version=fmt)
    assert md.format_version_at_least(threshold) is expected


@pytest.mark.parametrize(
    "fmt,threshold,expected",
    [
        ("1.2.3", "1.2.4", True),
        ("1.2.3", "1.2.3", False),
        ("1.2.3", "1.2.2", False),
        ("0.0.1", "0.0.2", True),
        ("2.0.0", "1.9.9", False),
    ],
)
def test_format_version_before(fmt, threshold, expected):
    md = BaseMetadata(format_version=fmt)
    assert md.format_version_before(threshold) is expected

# --- Normalization & happy paths --- #

def test_extensions_trim_keys_and_preserve_values():
    md = BaseMetadata(format_version="1.2.3", extensions={"  created_by  ": "alice"})
    # Keys should be trimmed
    assert set(md.extensions.keys()) == {"created_by"}
    assert md.extensions["created_by"] == "alice"


def test_extensions_empty_dict_passthrough():
    md = BaseMetadata(format_version="1.2.3", extensions={})
    assert md.extensions == {}


def test_extensions_assignment_duplicate_same_object_ok():
    md = BaseMetadata(format_version="1.2.3", extensions={"ok": 1})
    shared = object()
    md.extensions = {"  k": shared, "k ": shared}
    assert md.extensions == {"k": shared}


# --- Error paths in validator --- #

def test_extensions_reject_non_string_keys():
    with pytest.raises(ValidationError, match="(Input should be a valid string|string_type)"):
        BaseMetadata(format_version="1.2.3", extensions={42: "nope"})


def test_extensions_reject_empty_key_after_strip():
    with pytest.raises(ValidationError, match="Extension keys must be non-empty strings"):
        BaseMetadata(format_version="1.2.3", extensions={"   ": "nope"})


def test_extensions_duplicate_after_normalization_different_objects_raises():
    # Distinct objects to guarantee `is not` identity check is True
    v1, v2 = [], []
    with pytest.raises(ValidationError, match="Duplicate extension key after normalization: 'k'"):
        BaseMetadata(format_version="1.2.3", extensions={"k ": v1, "  k": v2})


def test_extensions_type_error_on_none():
    # Pydantic should reject None for a dict field before validator runs
    with pytest.raises(ValidationError, match="Input should be a valid dictionary"):
        BaseMetadata(format_version="1.2.3", extensions=None)  # type: ignore[arg-type]


# --- Assignment-time validation (validate_assignment=True) --- #

def test_extensions_assignment_trims_and_validates():
    md = BaseMetadata(format_version="1.2.3", extensions={"a": 1})
    md.extensions = {"  b  ": 2}
    assert md.extensions == {"b": 2}

    # Now try an invalid reassignment (empty key after strip)
    with pytest.raises(ValidationError, match="Extension keys must be non-empty strings"):
        md.extensions = {"   ": "bad"}  # triggers validator on assignment


def test_extensions_assignment_duplicate_after_normalization_raises():
    md = BaseMetadata(format_version="1.2.3", extensions={"ok": 1})
    v1, v2 = object(), object()
    with pytest.raises(ValidationError, match="Duplicate extension key after normalization: 'k'"):
        md.extensions = {"k ": v1, "  k": v2}  # same normalized key "k", different objects