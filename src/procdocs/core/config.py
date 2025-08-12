#!/usr/bin/env python3
"""
ProcDocs configuration loader.
"""

import os
from pathlib import Path
from typing import Any, Dict, Final, List

from procdocs.core.utils import merge_dicts, load_json_file

# --- Defaults & locations --- #

DEFAULT_CONFIG: Final[Dict[str, Any]] = {
    "schema_paths": [str(Path("./document_schemas").resolve())],
    "render_template_paths": [str(Path("./render_templates").resolve())],
    "logging": {"level": "INFO"},
}

GLOBAL_CONFIG_PATH: Final[Path] = Path.home() / ".config" / "procdocs" / "config.json"


# --- Public API --- #

def load_config() -> Dict[str, Any]:
    """
    Load ProcDocs configuration with layered precedence.

    Order:
        1. Built-in defaults
        2. Global config (~/.config/procdocs/config.json)
        3. Project config (./procdocs.json)
        4. Environment overrides:
           - PROCDOCS_SCHEMA_PATHS (pathsep-separated list)
           - PROCDOCS_LOG_LEVEL

    Returns:
        A merged configuration dictionary.
    """
    # 1) start with defaults
    config = dict(DEFAULT_CONFIG)

    # 2) global config
    config = merge_dicts(config, load_json_file(GLOBAL_CONFIG_PATH))

    # 3) project config
    project_path = Path.cwd() / "procdocs.json"
    config = merge_dicts(config, load_json_file(project_path))

    # 4) environment overrides
    schema_paths_env = os.getenv("PROCDOCS_SCHEMA_PATHS")
    if schema_paths_env:
        config["schema_paths"] = _split_paths_env(schema_paths_env)

    template_paths_env = os.getenv("PROCDOCS_RENDER_TEMPLATES_PATHS")
    if template_paths_env:
        config["render_template_paths"] = template_paths_env

    log_level_env = os.getenv("PROCDOCS_LOG_LEVEL")
    if log_level_env:
        config.setdefault("logging", {})["level"] = log_level_env

    return config


# --- Internals --- #

def _split_paths_env(value: str) -> List[str]:
    """
    Split a path-list env var on os.pathsep, trimming empties and expanding '~'.

    Example:
        "a:~/b:/tmp" on Unix  -> ["<cwd>/a", "/home/user/b", "/tmp"] (no resolve here)
    """
    parts = [p.strip() for p in value.split(os.pathsep)]
    return [str(Path(p).expanduser()) for p in parts if p]
