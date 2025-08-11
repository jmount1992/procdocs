#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from typing import Any, Optional, Dict, Type

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator,
    model_validator,
    model_serializer,
    computed_field,
    PrivateAttr,
)

from procdocs.core.schema.field_type import FieldType
from procdocs.core.schema.field_specs import (
    FieldSpec,
    StringSpec,
    NumberSpec,
    BooleanSpec,
    EnumSpec,
    ListSpec,
    DictSpec,
    RefSpec,
    rebuild_specs,
)
from procdocs.core import constants as C
from procdocs.core.utils import is_valid_fieldname_pattern


# Registry of which *flat* keys belong to which FieldType.
# For LIST we accept only "fields" (author never sees 'item').
SPEC_REGISTRY: Dict[FieldType, tuple[Type[BaseModel], set[str]]] = {
    FieldType.STRING: (StringSpec, {"pattern"}),
    FieldType.NUMBER: (NumberSpec, set()),
    FieldType.BOOLEAN: (BooleanSpec, set()),
    FieldType.ENUM:   (EnumSpec, {"options"}),
    FieldType.DICT:   (DictSpec, {"fields"}),
    FieldType.LIST:   (ListSpec, {"fields"}),
    FieldType.REF:    (RefSpec, {"cardinality", "allow_globs", "must_exist", "base_dir", "extensions"}),
}


class FieldDescriptor(BaseModel):
    """
    One field in a document meta‑schema.

    Authoring model:
      - Users write type‑specific keys at the top level (flat).
      - We pack them into a typed `spec` based on `fieldtype`.
      - When serializing, we flatten `spec` back to the top level.

    Common keys:
      - fieldname, fieldtype, required, description, default

    Type‑specific (live in `spec`; authored flat):
      - string:   pattern
      - enum:     options
      - dict:     fields (list[FieldDescriptor])
      - list:     fields (list[FieldDescriptor])  -> list of dicts with these fields
                   (if omitted: list of strings)
      - ref:      cardinality, allow_globs, must_exist, base_dir, extensions
    """

    model_config = ConfigDict(validate_assignment=True, extra="forbid")
    _path: str = PrivateAttr(default="")  # excluded from serialization

    # Common
    fieldname: str = Field(..., description="The name of the field")
    fieldtype: FieldType = Field(default=FieldType.STRING, description="Field type")
    required: bool = Field(default=True, description="Whether this field is required")
    description: str | None = Field(default=None, description="Human-readable description")
    default: Any | None = Field(default=None, description="Default value")

    # Per-type spec (packed/unpacked automatically)
    spec: FieldSpec | None = Field(default=None, description="Type-specific parameters")

    # --- Pre-parse: pack flat keys into spec --- #
    @model_validator(mode="before")
    @classmethod
    def _pack_flat_spec(cls, data: Any):
        if not isinstance(data, dict):
            return data

        # Missing fieldtype -> treat as STRING during packing
        raw_ft = data.get("fieldtype")
        ft = FieldType.parse(raw_ft) if raw_ft is not None else FieldType.STRING

        spec_model, allowed_keys = SPEC_REGISTRY.get(ft, (None, set()))
        if not spec_model:
            return data

        present_flat = {k: v for k, v in data.items() if k in allowed_keys}
        has_flat = bool(present_flat)
        has_spec = isinstance(data.get("spec"), dict)

        if has_flat and has_spec:
            raise ValueError("Provide either flat type-specific keys or 'spec', not both")

        # Flag keys that look like other types' keys (helps authoring errors)
        common = {"fieldname", "fieldtype", "required", "description", "default", "spec"}
        stray = {k for k in data.keys() if k not in (common | allowed_keys)}
        if stray:
            other_keys = set().union(*[ks for t, (_, ks) in SPEC_REGISTRY.items() if t != ft])
            suspicious = stray & other_keys
            if suspicious:
                # Render like "['pattern']" to match existing tests
                allowed_fmt = "[" + ", ".join(repr(k) for k in sorted(allowed_keys)) + "]"
                raise ValueError(
                    f"Unexpected key(s) for fieldtype '{ft.value}': {sorted(suspicious)}. "
                    f"Allowed: {allowed_fmt}"
                )

        # Synthesize spec from flat keys if provided
        if has_flat and not has_spec:
            synth = {"kind": ft.value, **present_flat}
            # Remove flat keys from top-level and insert 'spec'
            data = {k: v for k, v in data.items() if k not in allowed_keys}
            data["spec"] = synth

        # Also support minimal list authoring: fieldtype=list with no fields -> list[str]
        if not has_flat and not has_spec and ft == FieldType.LIST:
            data["spec"] = {"kind": "list"}  # fields omitted => default scalar list (str)

        return data

    # --- Computed UID --- #
    @computed_field  # type: ignore[prop-decorator]
    @property
    def uid(self) -> str:
        raw_encode = self._path.encode(C.DEFAULT_TEXT_ENCODING)
        return hashlib.sha1(raw_encode).hexdigest()[:10]

    # --- Validators --- #

    @field_validator("fieldtype", mode="before")
    @classmethod
    def _parse_fieldtype(cls, v):
        return FieldType.parse(v)

    @field_validator("fieldname", mode="before")
    @classmethod
    def _normalize_and_validate_fieldname(cls, v) -> str:
        s = "" if v is None else str(v).strip()
        if not s:
            raise ValueError("The 'fieldname' key is not set")
        if s in C.RESERVED_FIELDNAMES:
            raise ValueError(f"'{s}' is a reserved name and cannot be used")
        if not is_valid_fieldname_pattern(s):
            raise ValueError(
                f"The fieldname '{s}' must match the pattern '{C.FIELDNAME_ALLOWED_PATTERN.pattern}'"
            )
        return s

    @model_validator(mode="after")
    def _post(self):
        if self.fieldtype == FieldType.INVALID:
            raise ValueError("Unknown fieldtype; valid types are: string, number, boolean, list, dict, enum, ref")

        # Inject defaults for simple types when spec is omitted
        if self.spec is None:
            defaults: Dict[FieldType, FieldSpec] = {
                FieldType.STRING: StringSpec(),
                FieldType.NUMBER: NumberSpec(),
                FieldType.BOOLEAN: BooleanSpec(),
                FieldType.REF:    RefSpec(),
                FieldType.LIST:   ListSpec(),  # default scalar list (str)
            }
            if self.fieldtype in defaults:
                self.spec = defaults[self.fieldtype]
            else:
                # enum/dict require explicit spec (options/children)
                raise ValueError(f"{self.fieldtype.value} requires a 'spec' block")

        if getattr(self.spec, "kind", None) != self.fieldtype.value:
            raise ValueError(f"'spec.kind' ({self.spec.kind}) does not match fieldtype '{self.fieldtype.value}'")

        # Enum: extra checks
        if self.fieldtype == FieldType.ENUM:
            opts = [str(o) for o in self.spec.options]  # type: ignore[attr-defined]
            if any(s.strip() == "" for s in opts):
                raise ValueError("ENUM 'options' must not contain empty strings")
            if len(set(opts)) != len(opts):
                raise ValueError("ENUM 'options' contain duplicates")

        # DictSpec: min_length enforced by model; ListSpec: fields optional
        return self

    # --- Serializer: flatten spec back to top-level --- #
    @model_serializer(mode="plain")
    def _dump_flat(self):
        base = {
            "fieldname": self.fieldname,
            "fieldtype": self.fieldtype.value,
            "required": self.required,
            "description": self.description,
            "default": self.default,
        }
        _, keys = SPEC_REGISTRY[self.fieldtype]
        spec_dict = self.spec.model_dump() if self.spec else {}
        flat_spec: Dict[str, Any] = {}

        if self.fieldtype == FieldType.DICT:
            spec: DictSpec = self.spec  # type: ignore[assignment]
            flat_spec["fields"] = [fd._dump_flat() for fd in spec.fields]

        elif self.fieldtype == FieldType.LIST:
            spec: ListSpec = self.spec  # type: ignore[assignment]
            if spec.fields:
                flat_spec["fields"] = [fd._dump_flat() for fd in spec.fields]
            # else: scalar list default -> emit nothing extra

        else:
            # scalar/enums/refs: just copy allowed keys (pattern/options/ref knobs)
            for k in keys:
                if k in spec_dict:
                    flat_spec[k] = spec_dict[k]

        base = {k: v for k, v in base.items() if v is not None}
        return {**base, **flat_spec}


# Resolve forward refs for specs that point to FieldDescriptor
FieldDescriptor.model_rebuild()
rebuild_specs(FieldDescriptor)
