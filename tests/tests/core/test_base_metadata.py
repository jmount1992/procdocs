#!/usr/bin/env python3

import pytest

from procdocs.core.base.base_metadata import BaseMetadata


def test_valid_instantiation():
    md = BaseMetadata()
    assert md.format_version is None
    assert md.user_defined == []


@pytest.mark.parametrize("version,valid", [
    ("1.2.3", True),
    ("v1.2.3", False),
    ("1.2", False),
    (1.2, False),
])
def test_format_version_properties(version, valid):
    md = BaseMetadata()
    if valid:
        md.format_version = version
        assert md.format_version == version
    else:
        with pytest.raises(ValueError, match="Invalid format version"):
            md.format_version = version


@pytest.mark.parametrize("strict", [True, False])
@pytest.mark.parametrize("data,exception,errors", [
    ({}, "Missing required metadata fields", ["Missing required metadata fields: 'format_version'", "Invalid format version: 'None'"]),
    ({"format_versio": "0.0.0"}, "Missing required metadata fields", ["Missing required metadata fields: 'format_version'", "Invalid format version: 'None'"]),
    ({"format_version": "0.0"}, "Invalid format version", ["Invalid format version: '0.0'"])
])
def test_invalid_from_dict(strict, data, exception, errors):
    if strict:
        with pytest.raises(ValueError, match=exception):
            BaseMetadata.from_dict(data, strict=True)
        md = BaseMetadata.from_dict(data, strict=False)
        with pytest.raises(ValueError, match=exception):
            md.validate()

    md = BaseMetadata.from_dict(data, strict=False)
    result = md.validate(strict=False)
    assert len(result) == len(errors)
    for expected in errors:
        assert expected in result.errors

