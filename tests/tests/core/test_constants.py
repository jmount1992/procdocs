#!/usr/bin/env python3

import pytest

import procdocs.core.constants as const


# --- Basic sanity checks on constants --- #

def test_reserved_fieldnames_and_supported_ext():
    # Reserved fieldnames are as expected
    assert all(isinstance(x, str) for x in const.RESERVED_FIELDNAMES)

    # Supported schema extensions
    assert all(x.startswith(".") for x in const.SUPPORTED_SCHEMA_EXT)


def test_regex_patterns_match_expected_inputs():
    # Relaxed semver should match "v1", "1.2", "1.2.3"
    for val in ["v1", "1.2", "1.2.3"]:
        assert const.RELAXED_SEMVER_RE.fullmatch(val)

    # Strict semver matches only "x.y.z"
    assert const.STRICT_SEMVER_RE.fullmatch("1.2.3")
    assert not const.STRICT_SEMVER_RE.fullmatch("1.2")

    # Fieldname allowed pattern
    assert const.FIELDNAME_ALLOWED_RE.fullmatch("abc_123")
    assert not const.FIELDNAME_ALLOWED_RE.fullmatch("1abc")

    # Schema name allowed
    assert const.SCHEMA_NAME_ALLOWED_RE.fullmatch("schema-1.0")
    assert not const.SCHEMA_NAME_ALLOWED_RE.fullmatch("BadName")


def test_validate_constants_passes_for_default_version():
    const.validate_constants()  # no exception


def test_validate_constants_raises_for_invalid_version(monkeypatch):
    monkeypatch.setattr(const, "PROCDOCS_FORMAT_VERSION", "1.2")  # not strict semver
    with pytest.raises(RuntimeError, match="must be strict semver"):
        const.validate_constants()
