#!/usr/bin/env python3
import json
import os
from pathlib import Path
import pytest

import procdocs.core.config as cfg


# --- Helpers --- #

def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


# --- load_config: defaults only --- #

def test_load_config_defaults_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # No global or project config; no env vars
    monkeypatch.setattr(cfg, "GLOBAL_CONFIG_PATH", tmp_path / "no/such/config.json", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PROCDOCS_SCHEMA_PATHS", raising=False)
    monkeypatch.delenv("PROCDOCS_RENDER_TEMPLATES_PATHS", raising=False)
    monkeypatch.delenv("PROCDOCS_LOG_LEVEL", raising=False)

    # Expect exact defaults (don’t re-import; DEFAULT_CONFIG captured at module import)
    expected = cfg.DEFAULT_CONFIG
    result = cfg.load_config()

    assert result.keys() == expected.keys()
    assert result["schema_paths"] == expected["schema_paths"]
    assert result["render_template_paths"] == expected["render_template_paths"]
    assert result["logging"]["level"] == expected["logging"]["level"]


# --- Precedence: global < project < env --- #

def test_load_config_global_and_project_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    global_cfg = tmp_path / ".config/procdocs/config.json"
    project_dir = tmp_path / "proj"
    project_cfg = project_dir / "procdocs.json"

    _write_json(global_cfg, {
        "logging": {"level": "DEBUG"},
        "schema_paths": ["/global/schemas"],
        "extra": 1,
    })
    project_dir.mkdir(parents=True, exist_ok=True)
    _write_json(project_cfg, {
        "logging": {"level": "WARNING"},
        "schema_paths": ["/project/schemas"],
        "render_template_paths": ["/project/templates"],
    })

    monkeypatch.setattr(cfg, "GLOBAL_CONFIG_PATH", global_cfg, raising=False)
    monkeypatch.chdir(project_dir)
    monkeypatch.delenv("PROCDOCS_SCHEMA_PATHS", raising=False)
    monkeypatch.delenv("PROCDOCS_RENDER_TEMPLATES_PATHS", raising=False)
    monkeypatch.delenv("PROCDOCS_LOG_LEVEL", raising=False)

    result = cfg.load_config()

    # Project overrides global
    assert result["logging"]["level"] == "WARNING"
    assert result["schema_paths"] == ["/project/schemas"]
    assert result["render_template_paths"] == ["/project/templates"]
    # Values only in global propagate through
    assert result["extra"] == 1


# --- Env overrides --- #

def test_load_config_env_overrides_schema_and_log_level(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # No files
    monkeypatch.setattr(cfg, "GLOBAL_CONFIG_PATH", tmp_path / "missing.json", raising=False)
    monkeypatch.chdir(tmp_path)

    sep = os.pathsep
    env_val = f"a{sep}~/b{sep}/tmp{sep}"  # includes tilde + trailing sep + empty entry
    monkeypatch.setenv("PROCDOCS_SCHEMA_PATHS", env_val)
    monkeypatch.setenv("PROCDOCS_LOG_LEVEL", "ERROR")
    monkeypatch.delenv("PROCDOCS_RENDER_TEMPLATES_PATHS", raising=False)

    result = cfg.load_config()

    # Schema paths split + ~ expansion (do not resolve)
    paths = result["schema_paths"]
    assert paths[0] == "a"
    assert paths[1] != "~/b" and "b" in Path(paths[1]).parts  # tilde expanded
    assert Path(paths[2]).as_posix() == "/tmp"
    # Logging overridden
    assert result["logging"]["level"] == "ERROR"


def test_load_config_env_override_render_template_paths_raw_string(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Demonstrate current behavior: env value is taken as-is (string), not split.
    monkeypatch.setattr(cfg, "GLOBAL_CONFIG_PATH", tmp_path / "missing.json", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PROCDOCS_RENDER_TEMPLATES_PATHS", f"X{os.pathsep}Y")
    monkeypatch.delenv("PROCDOCS_SCHEMA_PATHS", raising=False)
    monkeypatch.delenv("PROCDOCS_LOG_LEVEL", raising=False)

    result = cfg.load_config()
    assert result["render_template_paths"] == f"X{os.pathsep}Y"  # current API


# --- _split_paths_env internals --- #

@pytest.mark.parametrize("value,expected", [
    ("a", ["a"]),
    (f"a{os.pathsep}b", ["a", "b"]),
    (f"{os.pathsep}a{os.pathsep}", ["a"]),              # leading/trailing empties dropped
    ("~/x", [str(Path("~/x").expanduser())]),          # tilde expansion
    ("  a  ", ["a"]),                                  # whitespace trim
])
def test_split_paths_env(value, expected):
    assert cfg._split_paths_env(value) == expected
