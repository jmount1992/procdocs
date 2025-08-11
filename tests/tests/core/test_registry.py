#!/usr/bin/env python3
import json
import pytest

from procdocs.core.registry import SchemaRegistry
from procdocs.core.constants import DEFAULT_TEXT_ENCODING


def _write_schema(tmp, name: str, structure):
    p = tmp / f"{name}.json"
    payload = {"metadata": {"schema_name": name}, "structure": structure}
    p.write_text(json.dumps(payload), encoding=DEFAULT_TEXT_ENCODING)
    return p


# --- Loading & lookup --- #

def test_registry_loads_schemas_and_resolves_by_name(tmp_path):
    root = tmp_path / "schemas"
    root.mkdir()

    _write_schema(root, "alpha", [{"fieldname": "id"}])
    _write_schema(root, "beta", [{"fieldname": "title"}])

    reg = SchemaRegistry([root])
    reg.load()

    assert reg.loaded is True
    assert reg.names() == ["alpha", "beta"]
    assert reg.get("Alpha").schema_name == "alpha"  # case-insensitive


def test_registry_require_raises_when_missing(tmp_path):
    reg = SchemaRegistry([tmp_path])
    reg.load()
    with pytest.raises(LookupError, match=r"not found"):
        reg.require("nope")


def test_registry_skips_invalid_files(tmp_path):
    root = tmp_path / "schemas"
    root.mkdir()

    # valid
    _write_schema(root, "ok", [{"fieldname": "id"}])

    # invalid: list field without proper child array (still structurally OK),
    # make it invalid by enum without options
    bad = root / "bad.json"
    bad.write_text(json.dumps({"metadata": {"schema_name": "bad"}, "structure": [{"fieldname": "x", "fieldtype": "enum"}]}),
                   encoding=DEFAULT_TEXT_ENCODING)

    reg = SchemaRegistry([root])
    reg.load()
    # Should only contain the valid one
    assert reg.names() == ["ok"]


def test_registry_handles_nonexistent_root(tmp_path):
    nonexist = tmp_path / "nope"
    reg = SchemaRegistry([nonexist])
    reg.load()
    assert reg.loaded is True
    assert reg.names() == []