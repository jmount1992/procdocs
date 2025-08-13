#!/usr/bin/env python3
"""
Purpose:
    Wires together the ProcDocs application context by merging configuration,
    initializing schema and template registries, and optionally preloading.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from procdocs.core.config import load_config
from procdocs.core.schema.registry import SchemaRegistry
from procdocs.core.render.registry import TemplateRegistry


# --- Data model --- #

@dataclass(frozen=True)
class AppContext:
    """Immutable container for configuration and registries."""
    config: Dict[str, Any]
    schemas: SchemaRegistry
    templates: TemplateRegistry


# --- Factory --- #

def build_context(
    *,
    config: Optional[Dict[str, Any]] = None,
    schema_roots: Optional[Iterable[Path]] = None,
    template_roots: Optional[Iterable[Path]] = None,
    preload: bool = True,
) -> AppContext:
    """
    Build an `AppContext`.

    Args:
        config:
            Pre-merged configuration. If omitted, `load_config()` is used.
        schema_roots:
            Optional override for schema search paths. Defaults to `config['schema_paths']`.
        template_roots:
            Optional override for template search paths. Defaults to `config['render_template_paths']`.
        preload:
            If True, eagerly loads registries; otherwise, caller may load later.

    Returns:
        AppContext: immutable bundle of config, schema registry, and template registry.
    """
    cfg = config or load_config()

    schema_paths = [Path(p) for p in (schema_roots or cfg.get("schema_paths", []))]
    schema_registry = SchemaRegistry(schema_paths)

    template_paths = [Path(p) for p in (template_roots or cfg.get("render_template_paths", []))]
    template_registry = TemplateRegistry(template_paths)

    if preload:
        schema_registry.load(clear=True)
        template_registry.load(clear=True)

    return AppContext(config=cfg, schemas=schema_registry, templates=template_registry)
