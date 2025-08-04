#!/usr/bin/env python3

import json
import os
from pathlib import Path
from typing import Dict, Any

DEFAULT_CONFIG = {
    "schema_paths": ["./document_schemas"],
    "default_schema": None,
    "logging": {
        "level": "INFO"
    }
}

GLOBAL_CONFIG_PATH = Path.home() / ".config" / "procdocs" / "config.json"


def load_json_file(path: Path) -> Dict[str, Any]:
    """Load JSON file from path. Returns empty dict if missing."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries (override wins)."""
    result = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = merge_dicts(result[k], v)
        else:
            result[k] = v
    return result


def load_config() -> Dict[str, Any]:
    """
    Load configuration in the following order:
    1. Default config (hardcoded)
    2. Global config (~/.config/procdocs/config.json)
    3. Project config (./procdocs.json)
    4. Environment overrides (PROC_DOCS_SCHEMA_PATHS, etc.)
    """

    # --- 1. start with defaults
    config = dict(DEFAULT_CONFIG)

    # --- 2. global config (~/.config/procdocs/config.json)
    config = merge_dicts(config, load_json_file(GLOBAL_CONFIG_PATH))

    # --- 3. project config (./procdocs.json)
    project_path = Path.cwd() / "procdocs.json"
    config = merge_dicts(config, load_json_file(project_path))

    # --- 4. environment overrides
    schema_paths_env = os.getenv("PROCDOCS_SCHEMA_PATHS")
    if schema_paths_env:
        config["schema_paths"] = schema_paths_env.split(os.pathsep)

    default_schema_env = os.getenv("PROCDOCS_DEFAULT_SCHEMA")
    if default_schema_env:
        config["default_schema"] = default_schema_env

    log_level_env = os.getenv("PROCDOCS_LOG_LEVEL")
    if log_level_env:
        config.setdefault("logging", {})["level"] = log_level_env

    return config
