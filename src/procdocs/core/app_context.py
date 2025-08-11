#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Iterable, Optional

from procdocs.core.config import load_config
from procdocs.core.schema.registry import SchemaRegistry 
from procdocs.core.render.registry import TemplateRegistry


@dataclass(frozen=True)
class AppContext:
    config: Dict[str, Any]
    schemas: SchemaRegistry
    templates: TemplateRegistry


def build_context(
    *,
    config: Optional[Dict[str, Any]] = None,
    schema_roots: Optional[Iterable[Path]] = None,
    template_roots: Optional[Iterable[Path]] = None,
    preload: bool = True,
) -> AppContext:
    cfg = config or load_config()

    schema_paths = [Path(p) for p in (schema_roots or cfg.get("schema_paths", []))]
    schema_registry = SchemaRegistry(schema_paths)

    template_paths = [Path(p) for p in (template_roots or cfg.get("render_template_paths", []))]
    template_registry = TemplateRegistry(template_paths)

    if preload:
        schema_registry.load(clear=True)
        template_registry.load(clear=True)
    return AppContext(config=cfg, schemas=schema_registry, templates=template_registry)
