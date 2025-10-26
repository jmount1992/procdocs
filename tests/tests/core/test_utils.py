#!/usr/bin/env python3
import json
from pathlib import Path
import pytest

from procdocs.core import utils


# --- Validation helpers --- #

@pytest.mark.parametrize("s,expected", [
    ("1.2.3", True),
    ("01.2.3", True),
    ("01.02.03", True),
    ("1.2", False),
    ("v1.2.3", False),
    ("", False),
])
def test_is_strict_semver(s, expected):
    assert utils.is_strict_semver(s) is expected


@pytest.mark.parametrize("s,expected", [
    ("1", True),
    ("1.2", True),
    ("1.2.3", True),
    ("v1", True),
    ("v1.2.3", True),
    ("1.2.3.4", False),
    ("", False),
])
def test_is_valid_version_relaxed(s, expected):
    assert utils.is_valid_version(s) is expected


@pytest.mark.parametrize("name,expected", [
    ("abc", True),
    ("_ok1", True),
    ("a_b_c_1", True),
    ("1bad", False),
    ("bad-name", False),
    ("", False),
])
def test_is_valid_fieldname_pattern(name, expected):
    assert utils.is_valid_fieldname_pattern(name) is expected


# --- Semver tuple & compare helpers --- #

def test_get_semver_tuple_ok_and_error():
    assert utils.get_semver_tuple("1.2.3") == (1, 2, 3)
    with pytest.raises(ValueError, match="Invalid semver string:"):
        utils.get_semver_tuple("1.2")


@pytest.mark.parametrize("a,b,expected", [
    ("1.2.3", "1.2.3", 0),
    ("1.2.3", "1.2.4", -1),
    ("2.0.0", "1.9.9", 1),
])
def test_compare_semver(a, b, expected):
    assert utils.compare_semver(a, b) == expected


def test_compare_semver_invalid_propagates():
    with pytest.raises(ValueError):
        utils.compare_semver("1.2", "1.2.3")


def test_semver_relation_helpers():
    assert utils.is_semver_equal("1.2.3", "1.2.3") is True
    assert utils.is_semver_at_least("1.2.3", "1.2.3") is True
    assert utils.is_semver_at_least("1.2.4", "1.2.3") is True
    assert utils.is_semver_after("1.2.4", "1.2.3") is True
    assert utils.is_semver_after("1.2.3", "1.2.3") is False
    assert utils.is_semver_before("1.2.2", "1.2.3") is True
    assert utils.is_semver_before("1.2.3", "1.2.3") is False


# --- Dict merge (recursive & overwrite) --- #

def test_merge_dicts_recursive_and_overwrite():
    base = {"a": 1, "b": {"x": 1, "y": 2}, "c": {"only_base": 1}, "d": 0}
    override = {"b": {"y": 20, "z": 30}, "c": 99, "e": {"new": 1}, "d": {"now_dict": True}}
    merged = utils.merge_dicts(base, override)
    assert merged == {
        "a": 1,
        "b": {"x": 1, "y": 20, "z": 30},  # dict merged
        "c": 99,                          # non-dict override replaces dict
        "d": {"now_dict": True},          # non-dict in base replaced by dict
        "e": {"new": 1},                  # new key added
    }
    # Original inputs unchanged
    assert base["b"] == {"x": 1, "y": 2}
    assert "z" not in base["b"]


# --- File I/O helpers --- #

def test_load_json_file_missing_returns_empty(tmp_path: Path):
    p = tmp_path / "missing.json"
    assert utils.load_json_file(p) == {}


def test_load_json_file_valid(tmp_path: Path):
    p = tmp_path / "ok.json"
    payload = {"a": 1, "b": {"c": [1, 2, 3]}}
    p.write_text(json.dumps(payload), encoding="utf-8")
    assert utils.load_json_file(p) == payload


def test_load_json_file_invalid_raises_valueerror(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid json}", encoding="utf-8")
    with pytest.raises(ValueError, match=r"Invalid JSON in .*bad\.json.*line .* col "):
        utils.load_json_file(p)
