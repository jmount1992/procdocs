#!/usr/bin/env python3
"""
Purpose:
    Implements the SchemaRegistry for ProcDocs, which discovers, loads,
    deduplicates, and caches JSON document schemas from given roots,
    providing query access to them.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from procdocs.core.constants import SUPPORTED_SCHEMA_EXT
from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.runtime_model import build_contents_adapter


@dataclass(frozen=True)
class SchemaEntry:
    """
    Lightweight record for a schema discovered on disk.
    - name: schema_name (lowercase if valid; otherwise derived from filename stem)
    - path: absolute path to the JSON file
    - valid: whether this is the selected, usable schema
    - reason: diagnostic text for invalid entries (parse error, duplicate dropped, etc.)
    - version: optional version extracted from the schema metadata (if available)
    """
    name: str
    path: Path
    valid: bool
    reason: Optional[str] = None
    version: Optional[str] = None


class SchemaRegistry:
    """
    Loads and caches `DocumentSchema` objects from one or more roots,
    builds contents adapters, and exposes entries (valid + invalid) for UX.

    Duplicate policy: newest mtime wins; older duplicates are marked invalid.
    """

    def __init__(self, roots: Iterable[Path]):
        self._roots = [Path(r) for r in roots]
        self._schemas: Dict[str, DocumentSchema] = {}         # valid winners by schema_name (lowercase)
        self._entries: List[SchemaEntry] = []                 # all scanned results (valid + invalid)
        self._valid_entries_by_name: Dict[str, SchemaEntry] = {}
        self._loaded: bool = False

    # --- Loading --- #

    def load(self, *, clear: bool = True) -> None:
        """
        Scan roots for schema files, parse, and apply duplicate resolution.

        Args:
            clear: if True, clears prior state before loading.
        """
        if clear:
            self._schemas.clear()
            self._entries.clear()
            self._valid_entries_by_name.clear()

        # Collect valid parse candidates per canonical name for duplicate resolution
        candidates: Dict[str, List[Tuple[Path, DocumentSchema, Optional[str]]]] = {}

        for root in self._roots:
            if not root.exists():
                continue

            # Find all supported schema files under this root
            for p in root.rglob("*"):
                if not p.is_file() or p.suffix.lower() not in SUPPORTED_SCHEMA_EXT:
                    continue

                try:
                    schema = DocumentSchema.from_file(p)
                    name = schema.schema_name.strip().lower()
                    # BUGFIX: version lives under metadata
                    version = schema.metadata.schema_version
                    candidates.setdefault(name, []).append((p.resolve(), schema, version))
                except Exception as e:
                    # Could not parse -> invalid entry recorded with filename stem as name
                    self._entries.append(
                        SchemaEntry(
                            name=p.stem.lower(),
                            path=p.resolve(),
                            valid=False,
                            reason=str(e),
                            version=None,
                        )
                    )

        # Resolve duplicates: newest mtime wins; losers recorded as invalid
        for name, items in candidates.items():
            # sort newest first by (mtime, path for stability)
            items.sort(key=lambda t: (t[0].stat().st_mtime, str(t[0])), reverse=True)
            winner_path, winner_schema, winner_version = items[0]

            # Record winner
            self._schemas[name] = winner_schema
            winner_entry = SchemaEntry(
                name=name,
                path=winner_path,
                valid=True,
                reason="kept",
                version=winner_version,
            )
            self._valid_entries_by_name[name] = winner_entry
            self._entries.append(winner_entry)

            # Warm adapter cache
            build_contents_adapter(winner_schema)

            # Record losers
            for loser_path, _loser_schema, _loser_version in items[1:]:
                self._entries.append(
                    SchemaEntry(
                        name=name,
                        path=loser_path,
                        valid=False,
                        reason="duplicate-dropped",
                        version=winner_version,
                    )
                )

        self._loaded = True

    # --- Query API --- #

    def get(self, schema_name: str) -> Optional[DocumentSchema]:
        """Return loaded (valid) schema by name (case-insensitive), or None."""
        return self._schemas.get(schema_name.strip().lower())

    def require(self, schema_name: str) -> DocumentSchema:
        """Return loaded schema by name or raise LookupError if not found/invalid."""
        s = self.get(schema_name)
        if not s:
            raise LookupError(f"Schema {schema_name!r} not found")
        return s

    def names(self) -> list[str]:
        """Sorted names of valid schemas."""
        return sorted(self._schemas.keys())

    def entries(self) -> List[SchemaEntry]:
        """All scanned entries (valid + invalid)."""
        return list(self._entries)

    def valid_entries(self) -> List[SchemaEntry]:
        """Only valid entries (winners)."""
        return [e for e in self._entries if e.valid]

    def invalid_entries(self) -> List[SchemaEntry]:
        """Only invalid entries (parse errors, duplicates dropped)."""
        return [e for e in self._entries if not e.valid]

    def get_entry(self, name: str) -> Optional[SchemaEntry]:
        """Get the valid entry by name (if any)."""
        return self._valid_entries_by_name.get(name.strip().lower())

    @property
    def loaded(self) -> bool:
        """True if a load() has completed."""
        return self._loaded

    @property
    def roots(self) -> List[Path]:
        """Roots scanned by this registry."""
        return list(self._roots)
