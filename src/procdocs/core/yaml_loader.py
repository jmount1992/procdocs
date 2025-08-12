#!/usr/bin/env python3

# ------------------------------------------------------------------------------
# PROTOTYPE / LEGACY NOTICE
#
# This module is part of the *prototype document render pipeline*.
# It exists only to support the experimental CLI for rendering documents and
# will likely be replaced in 0.2.0 when the render architecture is implemented.
#
# The final implementation will:
#   - Use FieldType.REF for recursive includes
#       (this file was created prior to that FieldType existing)
#   - Provide a new YAML loader with full include resolution
#
# Until then, treat this file as temporary/legacy code.
# ------------------------------------------------------------------------------

from pathlib import Path
from typing import Iterable, List
import yaml


class IncludeResolver:
    def __init__(self, roots: Iterable[Path]):
        self.roots = [r.resolve() for r in roots]

    def _guard(self, p: Path) -> Path:
        rp = p.resolve()
        if not any(str(rp).startswith(str(root)) for root in self.roots):
            raise ValueError(f"Include path '{p}' is outside allowed roots")
        return rp

    def read_yaml(self, path: Path) -> dict:
        with open(self._guard(path), "r", encoding="utf-8") as f:
            return yaml.load(f, Loader=make_loader(self))

    def read_many(self, pattern: Path) -> List[dict]:
        matched = sorted(pattern.parent.glob(pattern.name))
        return [self.read_yaml(p) for p in matched]


def make_loader(resolver: IncludeResolver):
    class Loader(yaml.SafeLoader):
        pass

    def _dir(loader: Loader) -> Path:
        # file being processed; SafeLoader exposes .name when reading from file
        if hasattr(loader.stream, "name"):
            return Path(loader.stream.name).parent
        return Path(".")

    def _construct_include(loader: Loader, node: yaml.Node):
        target = Path(loader.construct_scalar(node))
        base = _dir(loader)
        return resolver.read_yaml(base / target)

    def _construct_includeglob(loader: Loader, node: yaml.Node):
        pattern = Path(loader.construct_scalar(node))
        base = _dir(loader)
        return resolver.read_many(base / pattern)

    Loader.add_constructor("!include", _construct_include)
    Loader.add_constructor("!includeglob", _construct_includeglob)
    return Loader


def load_yaml_with_includes(path: Path, allowed_roots: Iterable[Path]) -> dict:
    resolver = IncludeResolver(allowed_roots)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=make_loader(resolver))
