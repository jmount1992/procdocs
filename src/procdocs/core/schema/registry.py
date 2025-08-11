#!/usr/bin/env python3

from pathlib import Path
from typing import Dict, Iterable, Optional

from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.runtime_model import build_contents_adapter


class SchemaRegistry:
    """
    Loads and caches DocumentSchemas (JSON-only) from one or more roots,
    and caches per-schema contents adapters for fast validation.
    """

    def __init__(self, roots: Iterable[Path]):
        self._roots = [Path(r) for r in roots]
        self._schemas: Dict[str, DocumentSchema] = {}  # key: schema_name (lowercase)
        self._loaded: bool = False

    def load(self, *, clear: bool = True) -> None:
        if clear:
            self._schemas.clear()
        for root in self._roots:
            if not root.exists():
                continue
            for p in root.rglob("*.json"):
                try:
                    schema = DocumentSchema.from_file(p)
                except Exception:
                    # Skip invalid schemas silently (tests assert this behavior)
                    continue
                self._schemas[schema.schema_name] = schema
                # Warm the adapter cache for this schema
                build_contents_adapter(schema)
        self._loaded = True

    def get(self, schema_name: str) -> Optional[DocumentSchema]:
        return self._schemas.get(schema_name.strip().lower())

    def require(self, schema_name: str) -> DocumentSchema:
        s = self.get(schema_name)
        if not s:
            raise LookupError(f"Schema '{schema_name}' not found")
        return s

    def names(self) -> list[str]:
        return sorted(self._schemas.keys())

    @property
    def loaded(self) -> bool:
        return self._loaded
