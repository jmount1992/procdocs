#!/usr/bin/env python3
import os
import json
import pytest
from pathlib import Path
import time

from procdocs.core.schema.registry import SchemaRegistry
from procdocs.core.constants import DEFAULT_TEXT_ENCODING


def _write_schema(path: Path, name: str, *, version=None, structure=None) -> Path:
    payload = {
        "metadata": {"schema_name": name} | ({"schema_version": version} if version is not None else {}),
        "structure": structure or [{"fieldname": "id"}],
    }
    path.write_text(json.dumps(payload), encoding=DEFAULT_TEXT_ENCODING)
    return path


# --- Loading & lookup --- #

def test_registry_loads_schemas_and_resolves_by_name(tmp_path):
    root = tmp_path / "schemas"
    root.mkdir()

    _write_schema(root / "alpha.json", "alpha", structure=[{"fieldname": "id"}])
    _write_schema(root / "beta.json", "beta", structure=[{"fieldname": "title"}])

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
    _write_schema(root / "ok.json", "ok", structure=[{"fieldname": "id"}])

    # invalid enum (missing options) -> should be skipped
    _write_schema(
        root / "bad.json",
        "bad",
        structure=[{"fieldname": "x", "fieldtype": "enum"}],  # no 'options'
    )

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


def test_deduplication_newest_mtime_wins_and_entries_mark_losers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "schemas"
    root.mkdir()

    # Two files with the same schema_name "alpha" — control mtimes so we know who wins
    older = _write_schema(root / "alpha_old.json", "alpha", version="v1")
    newer = _write_schema(root / "alpha_new.json", "alpha", version="v2")

    # Ensure deterministic order: set mtimes explicitly (newer wins)
    t0 = time.time()
    os.utime(older, (t0 - 10, t0 - 10))
    os.utime(newer, (t0, t0))

    # Also add a completely different schema to ensure normal behavior coexists
    _write_schema(root / "beta.json", "beta", version="b1")

    # Monkeypatch adapter to verify it's called only for the winner
    calls = []

    def fake_build_adapter(schema):
        calls.append(schema.schema_name)

    monkeypatch.setattr("procdocs.core.schema.registry.build_contents_adapter", fake_build_adapter)

    reg = SchemaRegistry([root])
    reg.load()

    # Winners by name
    assert reg.names() == ["alpha", "beta"]
    assert reg.get("Alpha").metadata.schema_version == "v2"  # newest version carried through
    assert reg.get_entry("alpha").version == "v2"

    # Entries should include both the kept winner and the dropped duplicate
    es = reg.entries()
    assert {e.name for e in es} == {"alpha", "beta"}
    winners = [e for e in es if e.valid]
    losers = [e for e in es if not e.valid]

    # One winner per name
    assert {(e.name, e.reason) for e in winners} == {("alpha", "kept"), ("beta", "kept")}
    # Duplicate loser recorded with same name and reason
    assert any(e.name == "alpha" and e.reason == "duplicate-dropped" for e in losers)

    # Adapter warmed exactly once per winning schema
    assert sorted(calls) == ["alpha", "beta"]

    # valid_entries / invalid_entries filters
    assert sorted(e.name for e in reg.valid_entries()) == ["alpha", "beta"]
    assert any(e.name == "alpha" and not e.valid for e in reg.invalid_entries())


def test_unsupported_extensions_are_ignored(tmp_path: Path):
    root = tmp_path / "schemas_ext"
    root.mkdir()

    _write_schema(root / "ok.json", "ok")
    (root / "ignore.txt").write_text("not a schema", encoding=DEFAULT_TEXT_ENCODING)
    (root / "also.ignore.yaml").write_text("{}", encoding=DEFAULT_TEXT_ENCODING)

    reg = SchemaRegistry([root])
    reg.load()

    assert reg.names() == ["ok"]
    assert reg.get("ok") is not None
    # Ensure no stray entries created for unsupported files
    assert all(e.path.suffix.lower() == ".json" for e in reg.entries())


def test_get_entry_and_roots_properties(tmp_path: Path):
    root1 = tmp_path / "a"
    root2 = tmp_path / "b"
    root1.mkdir()
    root2.mkdir()
    _write_schema(root1 / "x.json", "X")

    reg = SchemaRegistry([root1, root2])
    reg.load()

    assert [root1, root2] == reg.roots
    entry = reg.get_entry("x")
    assert entry and entry.valid and entry.name == "x"


def test_clear_false_appends_scan_results(tmp_path: Path):
    root = tmp_path / "schemas"
    root.mkdir()

    _write_schema(root / "one.json", "one")
    reg = SchemaRegistry([root])
    reg.load()
    entries_first = len(reg.entries())

    # Add a second schema, but load with clear=False; entries should grow
    _write_schema(root / "two.json", "two")
    reg.load(clear=False)
    entries_second = len(reg.entries())

    assert reg.names() == ["one", "two"]
    assert entries_second >= entries_first + 1  # at least one new entry appended


def test_registry_ignores_directories_in_scan(tmp_path):
    root = tmp_path / "schemas"
    root.mkdir()
    (root / "subdir").mkdir()  # ensure rglob("*") yields a non-file entry
    # still have at least one valid schema
    _write_schema(root / "ok.json", "ok", structure=[{"fieldname": "id"}])

    reg = SchemaRegistry([root])
    reg.load()

    assert reg.names() == ["ok"]


def test_registry_require_success(tmp_path):
    root = tmp_path / "schemas"
    root.mkdir()

    # use the helper you defined earlier
    _write_schema(root / "alpha.json", "alpha", structure=[{"fieldname": "id"}])

    reg = SchemaRegistry([root])
    reg.load()

    # success path: should return the loaded schema
    sch = reg.require("Alpha")  # case-insensitive
    assert sch.schema_name == "alpha"
