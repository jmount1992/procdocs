# procdocs/core/formatting.py
from __future__ import annotations
from typing import List, Iterable, Any


def format_pydantic_errors_simple(exc: Exception) -> List[str]:
    """
    Stable, minimal one-line formatting for Pydantic v2 ValidationError.
    Example: structure[1].fieldname: Field required
    Falls back to first-line of str(exc) if .errors() isn't available.
    """
    errors: Iterable[dict[str, Any]] | None = None
    if hasattr(exc, "errors") and callable(getattr(exc, "errors")):
        try:
            errors = exc.errors()  # pydantic v2 API
        except Exception:
            errors = None

    if not errors:
        return [str(exc).splitlines()[0]]

    msgs: List[str] = []
    for err in errors:
        loc = err.get("loc", ())
        msg = err.get("msg", "Validation error")
        parts: List[str] = []
        for seg in loc:
            if isinstance(seg, int):
                # append as index to previous segment if possible
                if parts and not parts[-1].endswith("]") and parts[-1] != ".":
                    parts[-1] = parts[-1] + f"[{seg}]"
                else:
                    parts.append(f"[{seg}]")
            else:
                if parts and not parts[-1].endswith("."):
                    parts.append(".")
                parts.append(str(seg))
        path = "".join(parts) if parts else "<root>"
        msgs.append(f"{path}: {msg}")
    return msgs
