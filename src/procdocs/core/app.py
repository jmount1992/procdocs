#!/usr/bin/env python3
"""
Application-wide context accessor (singleton-ish).

Use `get_context()` to obtain a loaded `AppContext`. You can force a reload or
override config/roots per call.
"""
from typing import Optional, Dict, Any, Iterable
from pathlib import Path

from procdocs.core.app_context import AppContext, build_context

# --- Module state --- #

_CTX: Optional[AppContext] = None


# --- Public API --- #

def get_context(
    *,
    force_reload: bool = False,
    config_override: Optional[Dict[str, Any]] = None,
    schema_roots_override: Optional[Iterable[Path]] = None,
    template_roots_override: Optional[Iterable[Path]] = None,
) -> AppContext:
    """
    Return the process-wide `AppContext`.

    Args:
        force_reload:
            If True, rebuilds the context even if one is already cached.
        config_override:
            Optional configuration dict to use instead of `load_config()`.
        schema_roots_override:
            Optional iterable of paths used instead of `config['schema_paths']`.
        template_roots_override:
            Optional iterable of paths used instead of `config['render_template_paths']`.

    Returns:
        A loaded `AppContext` instance.
    """
    global _CTX
    if (
        _CTX is None
        or force_reload
        or config_override
        or schema_roots_override
        or template_roots_override
    ):
        _CTX = build_context(
            config=config_override,
            schema_roots=schema_roots_override,
            template_roots=template_roots_override,
            preload=True,
        )
    return _CTX
