#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


def _template_name_from(path: Path) -> str:
    """
    Registry name derived from filename stem.
    Note: for 'report.md.j2' Path.stem -> 'report.md' (desired: keeps the logical format).
    """
    return path.stem


@dataclass(frozen=True)
class TemplateEntry:
    """
    Schema-agnostic template record.
    - name: simple registry key derived from filename stem
    - path: absolute path
    - valid: whether this entry is the selected winner for its name
    - reason: diagnostic text for invalid entries (duplicate-dropped, io-error, etc.)
    """
    name: str
    path: Path
    valid: bool
    reason: Optional[str] = None


class TemplateRegistry:
    """
    Finds Jinja2 templates without coupling to ProcDocs schemas.
    Duplicate policy: newest mtime wins; older duplicates marked invalid.
    """

    DEFAULT_PATTERNS: Sequence[str] = (
        "*.j2",
        "*.md.j2",
        "*.yaml.j2",
        "*.yml.j2",
        "*.html.j2",
        "*.txt.j2",
    )

    def __init__(self, roots: Iterable[Path], patterns: Optional[Sequence[str]] = None):
        self._roots = [Path(r) for r in roots]
        self._patterns = patterns or self.DEFAULT_PATTERNS
        self._by_name: Dict[str, TemplateEntry] = {}  # valid winners
        self._entries: List[TemplateEntry] = []       # all scans (valid + invalid)
        self._loaded = False

    # ----- Loading ------------------------------------------------------------

    def load(self, *, clear: bool = True) -> None:
        if clear:
            self._by_name.clear()
            self._entries.clear()

        # Collect candidates for duplicate resolution
        candidates: Dict[str, List[Path]] = {}
        for root in self._roots:
            if not root.exists():
                continue
            for pat in self._patterns:
                for p in root.rglob(pat):
                    name = _template_name_from(p)
                    candidates.setdefault(name, []).append(p.resolve())

        # Resolve duplicates: newest mtime wins
        for name, paths in candidates.items():
            try:
                paths.sort(key=lambda x: (x.stat().st_mtime, str(x)), reverse=True)
            except Exception as e:
                # If stat() fails for any path, mark those as invalid
                for p in paths:
                    try:
                        _ = p.stat()
                    except Exception as se:
                        self._entries.append(TemplateEntry(name=name, path=p, valid=False, reason=f"io-error: {se}"))
                # Continue with whatever remains usable
                paths = [p for p in paths if _safe_stat(p)]

            if not paths:
                continue

            winner = paths[0]
            winner_entry = TemplateEntry(name=name, path=winner, valid=True, reason="kept")
            self._by_name[name] = winner_entry
            self._entries.append(winner_entry)

            for loser in paths[1:]:
                self._entries.append(TemplateEntry(name=name, path=loser, valid=False, reason="duplicate-dropped"))

        self._loaded = True

    # ----- Query --------------------------------------------------------------

    def resolve(self, name: str) -> TemplateEntry:
        """Return the valid winner for a name, or raise if not found."""
        key = name.strip()
        entry = self._by_name.get(key)
        if not entry:
            raise FileNotFoundError(f"No template named '{name}'")
        return entry

    def get(self, name: str) -> Optional[TemplateEntry]:
        return self._by_name.get(name.strip())

    def names(self) -> List[str]:
        """Sorted list of valid template names."""
        return sorted(self._by_name.keys())

    def entries(self) -> List[TemplateEntry]:
        """All scanned entries (valid + invalid)."""
        return list(self._entries)

    def valid_entries(self) -> List[TemplateEntry]:
        return [e for e in self._entries if e.valid]

    def invalid_entries(self) -> List[TemplateEntry]:
        return [e for e in self._entries if not e.valid]

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def roots(self) -> List[Path]:
        return list(self._roots)


# ---- helpers ----------------------------------------------------------------

def _safe_stat(p: Path) -> bool:
    try:
        _ = p.stat()
        return True
    except Exception:
        return False
