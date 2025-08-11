#!/usr/bin/env python3

"""
runtime_model.py
================

This module provides a bridge between a static ProcDocs `DocumentSchema`
and a dynamic, runtime-generated Pydantic model that can be used to
validate document *contents* directly.

Purpose
-------
- Take a `DocumentSchema` instance (loaded from JSON) and compile it into
  an equivalent Pydantic model class at runtime.
- Use that model to validate `contents` dictionaries from YAML/JSON documents.
- Ensure validation behavior is consistent with the schema definition,
  including field types, required/optional status, patterns, and nested structures.

Usage
-----
    from procdocs.core.runtime_model import build_contents_adapter
    from procdocs.core.schema.document_schema import DocumentSchema

    schema = DocumentSchema.from_file("schemas/test_doc.json")
    ContentsModel = build_contents_adapter(schema)

    # Validate some loaded document contents
    document = ContentsModel(**document_dict["contents"])  # Raises ValidationError if invalid
"""


from typing import Any, Dict, List, Annotated, Literal, Iterable, Optional

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


# Cache of adapters keyed by schema fingerprint
_ADAPTER_CACHE: Dict[str, TypeAdapter] = {}


def build_contents_adapter(schema: DocumentSchema) -> TypeAdapter:
    """
    Build (or fetch cached) a Pydantic TypeAdapter that validates the *contents*
    dict for the given schema.
    """
    key = _schema_fingerprint(schema)
    if key in _ADAPTER_CACHE:
        return _ADAPTER_CACHE[key]

    model = _model_for_fields(schema.structure, model_name=f"{schema.schema_name}_Contents")
    adapter = TypeAdapter(model)
    _ADAPTER_CACHE[key] = adapter
    return adapter


# --- internals --- #

def _schema_fingerprint(schema: DocumentSchema) -> str:
    """
    Stable cache key over structure + schema identity.
    Uses canonical paths, field types, and type-specific knobs (pattern/options)
    where relevant.
    """
    parts: List[str] = [schema.schema_name, schema.format_version]
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


def _walk(fields: Iterable[FieldDescriptor]):
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
    model_config = ConfigDict(extra="forbid")


def _model_for_fields(fields: List[FieldDescriptor], model_name: str):
    """
    Create a Pydantic model class for an object with the given FieldDescriptors.
    Unknown keys will be rejected (extra="forbid" baked into the base).
    """
    field_defs: Dict[str, tuple[type, Any]] = {}
    for fd in fields:
        t = _py_type_for(fd)
        # required: `...`; optional: None; default: concrete default value
        default = ... if fd.required and fd.default is None else (fd.default if fd.default is not None else None)
        field_defs[fd.fieldname] = (t, default)
    return create_model(model_name, __base__=_StrictModel, **field_defs)  # type: ignore


def _py_type_for(fd: FieldDescriptor):
    """
    Map a FieldDescriptor to a Python typing object (or a Pydantic model)
    describing the expected value shape for contents validation.
    """
    ft = fd.fieldtype

    if ft == FieldType.STRING:
        pat = _string_pattern(fd)
        if pat:
            return Annotated[str, StringConstraints(pattern=pat)]
        return str

    if ft == FieldType.NUMBER:
        # Accept float (ints coerce to float automatically)
        return float

    if ft == FieldType.BOOLEAN:
        return bool

    if ft == FieldType.ENUM:
        opts = _enum_options(fd)
        # EnumSpec guarantees non-empty options by schema validation
        return Literal[tuple(opts)]  # type: ignore

    if ft == FieldType.DICT:
        sub = _model_for_fields(_dict_fields(fd), model_name=f"{fd.fieldname.title()}Obj")
        return sub

    if ft == FieldType.LIST:
        item_fd = _list_item(fd)
        elem_type = _py_type_for(item_fd)
        return List[elem_type]  # type: ignore

    if ft == FieldType.REF:
        # Treat as str or list[str] based on cardinality; path existence/globs are
        # enforced in higher layers (resolver/validator), not here.
        spec = _ref_spec(fd)
        return (str if spec.cardinality == "one" else List[str])  # type: ignore

    # Fallback (should not occur with prior schema validation)
    return Any


# ----- spec accessors (no legacy) ------------------------------------------------ #

def _string_pattern(fd: FieldDescriptor) -> Optional[str]:
    spec: StringSpec = fd.spec  # type: ignore[assignment]
    return spec.pattern if fd.fieldtype == FieldType.STRING else None


def _enum_options(fd: FieldDescriptor) -> List[str]:
    spec: EnumSpec = fd.spec  # type: ignore[assignment]
    return list(spec.options) if fd.fieldtype == FieldType.ENUM else []


def _dict_fields(fd: FieldDescriptor) -> List[FieldDescriptor]:
    spec: DictSpec = fd.spec  # type: ignore[assignment]
    return spec.fields


def _list_item(fd: FieldDescriptor) -> FieldDescriptor:
    spec: ListSpec = fd.spec  # type: ignore[assignment]
    return spec.item


def _ref_spec(fd: FieldDescriptor) -> RefSpec:
    spec: RefSpec = fd.spec  # type: ignore[assignment]
    return spec