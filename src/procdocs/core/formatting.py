#!/usr/bin/env python3
"""
Formatting helpers for ProcDocs.

- Stable, minimal one-line formatting for Pydantic v2 `ValidationError`.
"""
from __future__ import annotations

from typing import Any, Iterable, List, Sequence


# --- Public API --- #

def format_pydantic_errors_simple(exc: Exception) -> List[str]:
    """
    Return stable one-line messages from a Pydantic v2 ValidationError.

    Example:
        structure[1].fieldname: Field required

    Falls back to the first line of str(exc) if `exc.errors()` isn't available.
    """
    errors: Sequence[dict[str, Any]] | None = None

    if hasattr(exc, "errors") and callable(getattr(exc, "errors")):
        try:
            # Pydantic v2 API: returns a sequence of error dicts
            errors = exc.errors()  # type: ignore[assignment]
        except Exception:
            errors = None

    if not errors:
        return [str(exc).splitlines()[0]]

    msgs: List[str] = []
    for err in errors:
        loc = err.get("loc", ())
        msg = err.get("msg", "Validation error")
        path = _format_error_loc(loc)
        msgs.append(f"{path}: {msg}")
    return msgs


# --- Internals --- #

def _format_error_loc(loc: Iterable[Any]) -> str:
    """
    Convert a Pydantic error `loc` tuple into a dotted path with index suffixes.

    Examples:
        ('structure', 1, 'fieldname') -> "structure[1].fieldname"
        (0, 'items')                  -> "[0].items"
        ()                            -> "<root>"
    """
    parts: List[str] = []
    for seg in loc:
        if isinstance(seg, int):
            if parts:
                parts[-1] = f"{parts[-1]}[{seg}]"
            else:
                parts.append(f"[{seg}]")
        else:
            parts.append(str(seg))
    return ".".join(parts) if parts else "<root>"
