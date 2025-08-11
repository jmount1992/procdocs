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


from typing import Any, Dict, List, Annotated, Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter, create_model
from pydantic.types import StringConstraints

from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.schema.field_descriptor import FieldDescriptor
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
    # Stable key over structure + schema identity
    parts = [schema.schema_name, schema.format_version]
    for fd in _walk(schema.structure):
        parts.append(fd._path)
        parts.append(fd.fieldtype.value)
        if fd.options:
            parts.extend([f"opt:{o}" for o in fd.options])
        if fd.pattern:
            parts.append(f"pat:{fd.pattern}")
    return "|".join(parts)


def _walk(fields: List[FieldDescriptor]):
    for fd in fields:
        yield fd
        if fd.fields:
            yield from _walk(fd.fields)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _model_for_fields(fields: List[FieldDescriptor], model_name: str):
    """
    Create a Pydantic model class for an object with the given FieldDescriptors.
    Unknown keys will be rejected (extra="forbid" behavior baked into `create_model`).
    """
    field_defs: Dict[str, tuple[type, Any]] = {}
    for fd in fields:
        t = _py_type_for(fd)
        # required: `...` sentinel; optional: explicit `None` default; default: value
        default = ... if fd.required and fd.default is None else (fd.default if fd.default is not None else None)
        field_defs[fd.fieldname] = (t, default)
    return create_model(model_name, __base__=_StrictModel, **field_defs)  # type: ignore


def _py_type_for(fd: FieldDescriptor):
    ft = fd.fieldtype

    if ft == FieldType.STRING:
        # Attach regex constraint to strings when available
        if fd.pattern:
            return Annotated[str, StringConstraints(pattern=fd.pattern)]
        return str

    if ft == FieldType.NUMBER:
        # Accept float (ints coerce to float automatically)
        return float

    if ft == FieldType.BOOLEAN:
        return bool

    if ft == FieldType.ENUM and fd.options:
        # Exact membership with Literal[...] of stringified options
        return Literal[tuple(str(o) for o in fd.options)]  # type: ignore

    if ft == FieldType.DICT:
        sub = _model_for_fields(fd.fields or [], model_name=f"{fd.fieldname.title()}Obj")
        return sub

    if ft == FieldType.LIST:
        if fd.fields:
            elem = _model_for_fields(fd.fields, model_name=f"{fd.fieldname.title()}Item")
        else:
            # Scalar list without element schema — default to string elements
            elem = str
        return List[elem]  # type: ignore

    # Fallback (shouldn’t occur with prior validation)
    return Any
