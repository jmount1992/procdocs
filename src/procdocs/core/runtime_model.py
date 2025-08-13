#!/usr/bin/env python3
"""
Purpose:
    Bridges a static ProcDocs DocumentSchema to a runtime-generated Pydantic
    model/TypeAdapter for validating document contents, with caching keyed
    by a schema fingerprint.
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, Iterable, Optional

from pydantic import BaseModel, ConfigDict, TypeAdapter, create_model
from pydantic.types import StringConstraints

from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.schema.field_descriptor import (
    FieldDescriptor,
    DictSpec,
    ListSpec,
    EnumSpec,
    StringSpec,
    RefSpec,
)
from procdocs.core.schema.field_type import FieldType


# --- Adapter cache --- #

# Cache of adapters keyed by schema fingerprint
_ADAPTER_CACHE: Dict[str, TypeAdapter] = {}


def build_contents_adapter(schema: DocumentSchema) -> TypeAdapter:
    """
    Build (or fetch from cache) a Pydantic TypeAdapter that validates the
    `contents` mapping for the given DocumentSchema.

    Behavior:
        - Compiles a strict model (extra="forbid") mirroring the schema's field types,
          required/optional flags, string patterns, enum options, nested dict/list shapes,
          and ref cardinality (str vs list[str]).
        - Caches adapters by a stable fingerprint of schema name, format version, and structure.

    Args:
        schema: The loaded DocumentSchema to compile.

    Returns:
        A TypeAdapter that can validate Python dicts (or JSON) representing document contents.

    Example:
        adapter = build_contents_adapter(schema)
        contents = adapter.validate_python(doc["contents"])  # raises ValidationError if invalid
    """
    key = _schema_fingerprint(schema)
    if key in _ADAPTER_CACHE:
        return _ADAPTER_CACHE[key]

    model = _model_for_fields(schema.structure, model_name=f"{schema.schema_name}_Contents")
    adapter = TypeAdapter(model)
    _ADAPTER_CACHE[key] = adapter
    return adapter


# --- Internals --- #

def _schema_fingerprint(schema: DocumentSchema) -> str:
    """
    Stable cache key over structure + schema identity.

    Incorporates canonical paths, field types, and type-specific knobs
    (e.g., string pattern, enum options, ref cardinality).
    """
    parts: list[str] = [schema.schema_name, schema.format_version]
    for fd in _walk(schema.structure):
        parts.append(fd._path)
        parts.append(fd.fieldtype.value)
        if fd.fieldtype == FieldType.STRING:
            pat = _string_pattern(fd)
            if pat:
                parts.append(f"pat:{pat}")
        elif fd.fieldtype == FieldType.ENUM:
            for o in _enum_options(fd):
                parts.append(f"opt:{o}")
        elif fd.fieldtype == FieldType.REF:
            ref = _ref_spec(fd)
            parts.append(f"ref:{ref.cardinality}")
    return "|".join(parts)


def _walk(fields: Iterable[FieldDescriptor]) -> Iterable[FieldDescriptor]:
    """
    Depth-first walk over FieldDescriptors, descending into DICT/LIST children
    via their specs.
    """
    for fd in fields:
        yield fd
        if fd.fieldtype == FieldType.DICT:
            spec: DictSpec = fd.spec  # type: ignore[assignment]
            for child in spec.fields:
                yield from _walk([child])
        elif fd.fieldtype == FieldType.LIST:
            spec: ListSpec = fd.spec  # type: ignore[assignment]
            yield from _walk([spec.item])


class _StrictModel(BaseModel):
    """Base model with `extra="forbid"` baked in for generated models."""
    model_config = ConfigDict(extra="forbid")


def _model_for_fields(fields: list[FieldDescriptor], model_name: str) -> type[_StrictModel]:
    """
    Create a Pydantic model class for an object with the given FieldDescriptors.

    Unknown keys are rejected via the `_StrictModel` base.
    """
    field_defs: Dict[str, tuple[type, Any]] = {}
    for fd in fields:
        t = _py_type_for(fd)
        # required: `...`; optional: None; default: concrete default value
        default = ... if fd.required and fd.default is None else (fd.default if fd.default is not None else None)
        field_defs[fd.fieldname] = (t, default)
    return create_model(model_name, __base__=_StrictModel, **field_defs)  # type: ignore[return-value]


def _py_type_for(fd: FieldDescriptor) -> type | object:
    """
    Map a FieldDescriptor to a typing object (or generated Pydantic model)
    describing the expected value shape for contents validation.
    """
    ft = fd.fieldtype

    if ft == FieldType.STRING:
        pat = _string_pattern(fd)
        if pat:
            return Annotated[str, StringConstraints(pattern=pat)]  # type: ignore[name-defined]  # pyright: ignore[reportUndefinedVariable]
        return str

    if ft == FieldType.NUMBER:
        # Accept float (ints coerce to float automatically)
        return float

    if ft == FieldType.BOOLEAN:
        return bool

    if ft == FieldType.ENUM:
        opts = _enum_options(fd)
        # Note: relying on Literal[(...)] shape as accepted by Pydantic's TypeAdapter.
        # This intentionally constructs a Literal with the tuple of allowed choices.
        from typing import Literal  # local import to avoid polluting module namespace
        return Literal[tuple(opts)]  # type: ignore[misc,valid-type]

    if ft == FieldType.DICT:
        sub = _model_for_fields(_dict_fields(fd), model_name=f"{fd.fieldname.title()}Obj")
        return sub

    if ft == FieldType.LIST:
        item_fd = _list_item(fd)
        elem_type = _py_type_for(item_fd)
        return list[elem_type]  # type: ignore[valid-type]

    if ft == FieldType.REF:
        # Treat as str or list[str] based on cardinality; path existence/globs are
        # enforced in higher layers (resolver/validator), not here.
        spec = _ref_spec(fd)
        return (str if spec.cardinality == "one" else list[str])

    # Fallback (should not occur with prior schema validation)
    return Any


# --- Spec Accessors --- #

def _string_pattern(fd: FieldDescriptor) -> Optional[str]:
    spec: StringSpec = fd.spec  # type: ignore[assignment]
    return spec.pattern if fd.fieldtype == FieldType.STRING else None


def _enum_options(fd: FieldDescriptor) -> list[str]:
    spec: EnumSpec = fd.spec  # type: ignore[assignment]
    return list(spec.options) if fd.fieldtype == FieldType.ENUM else []


def _dict_fields(fd: FieldDescriptor) -> list[FieldDescriptor]:
    spec: DictSpec = fd.spec  # type: ignore[assignment]
    return spec.fields


def _list_item(fd: FieldDescriptor) -> FieldDescriptor:
    spec: ListSpec = fd.spec  # type: ignore[assignment]
    return spec.item


def _ref_spec(fd: FieldDescriptor) -> RefSpec:
    spec: RefSpec = fd.spec  # type: ignore[assignment]
    return spec
