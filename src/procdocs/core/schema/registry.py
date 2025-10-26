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
from typing import Dict, Iterable, List, Optional

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
        Newest mtime wins among duplicates; losers are recorded as invalid.

        Args:
            clear: if True, clears prior state before loading.
        """
        if clear:
            self._clear_state()

        candidates: dict[str, list[tuple[Path, DocumentSchema, Optional[str]]]] = {}

        for p in self._iter_schema_files():
            schema, err = self._parse_schema_file(p)
            if err:
                self._record_invalid_entry(p, err)
                continue
            self._add_candidate(candidates, schema, p)

        self._resolve_duplicates(candidates)
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

    # --- Loading Helpers --- #
    def _clear_state(self) -> None:
        self._schemas.clear()
        self._entries.clear()
        self._valid_entries_by_name.clear()

    def _iter_schema_files(self):
        for root in self._roots:
            if not root.exists():
                continue
            # Avoid filtering twice; check suffix once here
            for p in root.rglob("*"):
                if p.is_file() and p.suffix.lower() in SUPPORTED_SCHEMA_EXT:
                    yield p

    def _parse_schema_file(self, path: Path) -> tuple[DocumentSchema | None, str | None]:
        try:
            s = DocumentSchema.from_file(path)
            # BUGFIX: version lives under metadata
            ver = getattr(getattr(s, "metadata", None), "schema_version", None)
            # Stash version on the schema for later, or just return it via entries
            s.__dict__.setdefault("_registry_version", ver)  # harmless, optional
            return s, None
        except Exception as e:
            return None, str(e)

    def _record_invalid_entry(self, path: Path, reason: str) -> None:
        self._entries.append(
            SchemaEntry(
                name=path.stem.lower(),
                path=path.resolve(),
                valid=False,
                reason=reason,
                version=None,
            )
        )

    def _add_candidate(
        self,
        candidates: dict[str, list[tuple[Path, DocumentSchema, Optional[str]]]],
        schema: DocumentSchema,
        path: Path,
    ) -> None:
        name = schema.schema_name.strip().lower()
        version = getattr(schema, "_registry_version", None)
        candidates.setdefault(name, []).append((path.resolve(), schema, version))

    def _select_winner(self, items: list[tuple[Path, DocumentSchema, Optional[str]]]):
        # newest mtime wins; tie-break by path for stability
        items.sort(key=lambda t: (t[0].stat().st_mtime, str(t[0])), reverse=True)
        return items[0], items[1:]

    def _record_winner(self, name: str, path: Path, schema: DocumentSchema, version: Optional[str]) -> None:
        self._schemas[name] = schema
        entry = SchemaEntry(name=name, path=path, valid=True, reason="kept", version=version)
        self._valid_entries_by_name[name] = entry
        self._entries.append(entry)
        # Warm adapter cache
        build_contents_adapter(schema)

    def _record_losers(self, name: str, losers: list[tuple[Path, DocumentSchema, Optional[str]]], version: Optional[str]) -> None:
        for loser_path, _ls, _ver in losers:
            self._entries.append(
                SchemaEntry(
                    name=name,
                    path=loser_path,
                    valid=False,
                    reason="duplicate-dropped",
                    version=version,
                )
            )

    def _resolve_duplicates(self, candidates: dict[str, list[tuple[Path, DocumentSchema, Optional[str]]]]) -> None:
        for name, items in candidates.items():
            (win_path, win_schema, win_ver), losers = self._select_winner(items)
            self._record_winner(name, win_path, win_schema, win_ver)
            self._record_losers(name, losers, win_ver)
