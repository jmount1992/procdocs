#!/usr/bin/env python3
from typing import Optional, Dict, Any, Iterable
from pathlib import Path
from procdocs.core.app_context import AppContext, build_context

_CTX: Optional[AppContext] = None

def get_context(
    *,
    force_reload: bool = False,
    config_override: Optional[Dict[str, Any]] = None,
    schema_roots_override: Optional[Iterable[Path]] = None,
    template_roots_override: Optional[Iterable[Path]] = None,
) -> AppContext:
    global _CTX
    if _CTX is None or force_reload or config_override or schema_roots_override or template_roots_override:
        _CTX = build_context(
            config=config_override,
            schema_roots=schema_roots_override,
            template_roots=template_roots_override,
            preload=True,
        )
    return _CTX
