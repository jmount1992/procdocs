#!/usr/bin/env python3
"""
Purpose:
    Generic schema-driven reference resolver for ProcDocs documents.

    Walks a document's `contents` using the corresponding DocumentSchema.
    Whenever a FieldDescriptor has fieldtype == REF, it resolves the referenced
    path (and optionally loads/embeds a referenced ProcDocs YAML document).

Design:
    - Resolution is schema-driven: only fields declared as FieldType.REF are resolved.
    - The original field value is preserved (e.g. 'filepath' remains a string).
    - Optional embedded payload is stored alongside the ref using RefSpec.embed_as.

Expected RefSpec extensions (breaking-change friendly MVP):
    - ref_kind: "file" | "procdocs_document" (default: "file")
    - document_type: optional str (expected referenced metadata.document_type)
    - embed_as: str (default: "resolved")
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from procdocs.core.document.document import Document
from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.schema.field_descriptor import FieldDescriptor, DictSpec, ListSpec
from procdocs.core.schema.field_type import FieldType
from procdocs.core.schema.registry import SchemaRegistry


class ResolveError(RuntimeError):
    """Raised when reference resolution fails in strict mode."""


@dataclass(frozen=True)
class ResolveResult:
    """Resolved contents plus non-fatal warnings (when strict=False)."""
    contents: Dict[str, Any]
    warnings: List[str]


class ReferenceResolver:
    """
    Resolves FieldType.REF fields in a document based on its schema.

    Notes:
        - This resolver assumes the document has already been validated against the schema.
        - It performs existence/extension checks based on RefSpec.
        - If ref_kind == 'document', it loads Document.from_file() and validates using the registry.
    """

    def resolve(
        self,
        *,
        contents: Dict[str, Any],
        schema: DocumentSchema,
        registry: SchemaRegistry,
        base_dir: Path,
        strict: bool = True,
    ) -> ResolveResult:
        if not isinstance(contents, dict):
            raise ResolveError("Document contents must be a dict/object at the root")

        warnings: List[str] = []
        resolved_root = dict(contents)

        self._resolve_dict_fields(
            parent=resolved_root,
            fields=schema.structure,
            registry=registry,
            base_dir=Path(base_dir),
            strict=strict,
            warnings=warnings,
            at_path="contents",
        )

        return ResolveResult(contents=resolved_root, warnings=warnings)

    # --- Core traversal --- #

    def _resolve_dict_fields(
        self,
        *,
        parent: Dict[str, Any],
        fields: Iterable[FieldDescriptor],
        registry: SchemaRegistry,
        base_dir: Path,
        strict: bool,
        warnings: List[str],
        at_path: str,
    ) -> None:
        for fd in fields:
            key = fd.fieldname
            if key not in parent:
                continue  # missing optional; document validation already handled required fields

            value = parent.get(key)

            if fd.fieldtype == FieldType.DICT:
                if isinstance(value, dict):
                    spec: DictSpec = fd.spec  # type: ignore[assignment]
                    self._resolve_dict_fields(
                        parent=value,
                        fields=spec.fields,
                        registry=registry,
                        base_dir=base_dir,
                        strict=strict,
                        warnings=warnings,
                        at_path=f"{at_path}.{key}",
                    )
                else:
                    self._warn_or_raise(
                        f"{at_path}.{key}: expected dict/object",
                        strict=strict,
                        warnings=warnings,
                    )

            elif fd.fieldtype == FieldType.LIST:
                spec: ListSpec = fd.spec  # type: ignore[assignment]
                if isinstance(value, list):
                    self._resolve_list_items(
                        items=value,
                        item_fd=spec.item,
                        registry=registry,
                        base_dir=base_dir,
                        strict=strict,
                        warnings=warnings,
                        at_path=f"{at_path}.{key}",
                    )
                else:
                    self._warn_or_raise(
                        f"{at_path}.{key}: expected list",
                        strict=strict,
                        warnings=warnings,
                    )

            elif fd.fieldtype == FieldType.REF:
                # Resolve and optionally embed into the parent dict
                self._resolve_ref_field_into_parent(
                    parent=parent,
                    field=fd,
                    value=value,
                    registry=registry,
                    base_dir=base_dir,
                    strict=strict,
                    warnings=warnings,
                    at_path=f"{at_path}.{key}",
                )

            else:
                # scalar/enum/boolean/number: nothing to resolve
                continue

    def _resolve_list_items(
        self,
        *,
        items: List[Any],
        item_fd: FieldDescriptor,
        registry: SchemaRegistry,
        base_dir: Path,
        strict: bool,
        warnings: List[str],
        at_path: str,
    ) -> None:
        # Each element must conform to item_fd schema; we resolve nested content inside each element.
        for i, elem in enumerate(items):
            elem_path = f"{at_path}[{i}]"

            if item_fd.fieldtype == FieldType.DICT:
                if isinstance(elem, dict):
                    spec: DictSpec = item_fd.spec  # type: ignore[assignment]
                    self._resolve_dict_fields(
                        parent=elem,
                        fields=spec.fields,
                        registry=registry,
                        base_dir=base_dir,
                        strict=strict,
                        warnings=warnings,
                        at_path=elem_path,
                    )
                else:
                    self._warn_or_raise(f"{elem_path}: expected dict/object", strict=strict, warnings=warnings)

            elif item_fd.fieldtype == FieldType.LIST:
                # Nested lists are allowed; recurse
                spec: ListSpec = item_fd.spec  # type: ignore[assignment]
                if isinstance(elem, list):
                    self._resolve_list_items(
                        items=elem,
                        item_fd=spec.item,
                        registry=registry,
                        base_dir=base_dir,
                        strict=strict,
                        warnings=warnings,
                        at_path=elem_path,
                    )
                else:
                    self._warn_or_raise(f"{elem_path}: expected list", strict=strict, warnings=warnings)

            elif item_fd.fieldtype == FieldType.REF:
                # A list-of-refs as direct elements (rare). We can’t embed sibling keys here, so we replace element with a dict.
                resolved = self._resolve_ref_value(
                    field=item_fd,
                    value=elem,
                    registry=registry,
                    base_dir=base_dir,
                    strict=strict,
                    warnings=warnings,
                    at_path=elem_path,
                )
                if isinstance(resolved, dict):
                    items[i] = resolved

            else:
                # scalar element; nothing to resolve
                continue

    # --- Ref resolution --- #

    def _resolve_ref_field_into_parent(
        self,
        *,
        parent: Dict[str, Any],
        field: FieldDescriptor,
        value: Any,
        registry: SchemaRegistry,
        base_dir: Path,
        strict: bool,
        warnings: List[str],
        at_path: str,
    ) -> None:
        """
        Resolve a ref field inside a dict parent. Preserve the original field value,
        but optionally add embedded content under RefSpec.embed_as.
        """
        resolved = self._resolve_ref_value(
            field=field,
            value=value,
            registry=registry,
            base_dir=base_dir,
            strict=strict,
            warnings=warnings,
            at_path=at_path,
        )
        if isinstance(resolved, dict):
            # Merge embedded keys into the parent dict. We do not overwrite the original ref field.
            for k, v in resolved.items():
                if k == field.fieldname:
                    continue
                parent[k] = v

    def _resolve_ref_value(
        self,
        *,
        field: FieldDescriptor,
        value: Any,
        registry: SchemaRegistry,
        base_dir: Path,
        strict: bool,
        warnings: List[str],
        at_path: str,
    ) -> Dict[str, Any] | None:
        """
        Returns a dict containing:
          { <fieldname>: <original>, <embed_as>: <embedded>, <embed_as>_metadata: ... , resolved_path: ... }

        For file refs: embed may be omitted; we still provide resolved_path for convenience.
        """
        if not isinstance(value, str) or not value.strip():
            self._warn_or_raise(f"{at_path}: expected non-empty string path", strict=strict, warnings=warnings)
            return None

        spec = field.spec
        # RefSpec is a pydantic model; access safely
        ref_kind = getattr(spec, "ref_kind", "file")  # "file" | "procdocs_document"
        document_type = getattr(spec, "document_type", None)
        embed_as = getattr(spec, "embed_as", "resolved")

        resolved_path = self._resolve_path(
            raw=value,
            base_dir=base_dir,
            spec_base_dir=getattr(spec, "base_dir", None),
        )

        # Extension restriction
        exts = getattr(spec, "extensions", None)
        if exts and resolved_path.suffix.lower() not in {e.lower() for e in exts}:
            self._warn_or_raise(
                f"{at_path}: {value!r} has extension {resolved_path.suffix!r} not in allowed {exts!r}",
                strict=strict,
                warnings=warnings,
            )
            return {field.fieldname: value, "resolved_path": str(resolved_path)}

        must_exist = bool(getattr(spec, "must_exist", False))
        if must_exist and not resolved_path.exists():
            self._warn_or_raise(
                f"{at_path}: referenced file {str(resolved_path)!r} does not exist (from {value!r})",
                strict=strict,
                warnings=warnings,
            )
            return {field.fieldname: value, "resolved_path": str(resolved_path)}

        # For plain file refs, we’re done.
        if ref_kind != "procdocs_document":
            return {field.fieldname: value, "resolved_path": str(resolved_path)}

        # Document ref: load + validate + embed
        try:
            child = Document.from_file(resolved_path)
        except Exception as e:
            self._warn_or_raise(
                f"{at_path}: failed to load referenced document {str(resolved_path)!r}: {e}",
                strict=strict,
                warnings=warnings,
            )
            return {field.fieldname: value, "resolved_path": str(resolved_path)}

        child_errors = child.validate(registry=registry)
        if child_errors:
            self._warn_or_raise(
                f"{at_path}: referenced document {resolved_path.name!r} is invalid:\n  - " + "\n  - ".join(child_errors),
                strict=strict,
                warnings=warnings,
            )
            return {field.fieldname: value, "resolved_path": str(resolved_path)}

        if document_type and child.metadata.document_type != document_type:
            self._warn_or_raise(
                f"{at_path}: referenced document type {child.metadata.document_type!r} != expected {document_type!r}",
                strict=strict,
                warnings=warnings,
            )
            return {field.fieldname: value, "resolved_path": str(resolved_path)}

        return {
            field.fieldname: value,
            "resolved_path": str(resolved_path),
            embed_as: dict(child.contents or {}),
            f"{embed_as}_metadata": child.metadata.model_dump(),
        }

    # --- Path helpers --- #

    @staticmethod
    def _resolve_path(*, raw: str, base_dir: Path, spec_base_dir: Optional[str]) -> Path:
        """
        Resolve a raw path relative to:
          - spec_base_dir (if provided), otherwise
          - base_dir
        """
        raw_path = Path(raw)
        if raw_path.is_absolute():
            return raw_path

        if spec_base_dir:
            return (base_dir / spec_base_dir / raw).resolve()

        return (base_dir / raw).resolve()

    @staticmethod
    def _warn_or_raise(msg: str, *, strict: bool, warnings: List[str]) -> None:
        if strict:
            raise ResolveError(msg)
        warnings.append(msg)
