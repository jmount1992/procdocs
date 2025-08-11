# procdocs/core/render/template_registry.py

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Optional


Key = Tuple[str, Optional[str]]  # (document_type, schema_version or None)


@dataclass(frozen=True)
class TemplateEntry:
    name: str           # e.g., "complete_test.html.j2"
    path: Path          # absolute path to template file


class TemplateRegistry:
    def __init__(self):
        self._by_key: Dict[Key, TemplateEntry] = {}

    def register(self, document_type: str, version: Optional[str], path: Path):
        key = (document_type, version)
        self._by_key[key] = TemplateEntry(name=path.name, path=path.resolve())

    def resolve(self, document_type: str, version: Optional[str]) -> TemplateEntry:
        # exact match
        key = (document_type, version)
        if key in self._by_key:
            return self._by_key[key]
        # wildcard fallback
        key_any = (document_type, None)
        if key_any in self._by_key:
            return self._by_key[key_any]
        raise FileNotFoundError(f"No template for (type='{document_type}', version='{version}')")
