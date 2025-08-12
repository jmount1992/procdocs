#!/usr/bin/env python3
"""
FieldDescriptor: the core Pydantic model describing one schema field.

Authoring flow:
- Users write flat JSON: common keys plus type-specific keys at the top level.
- Pre-parse packs those into a typed `spec` based on `fieldtype`.
- Serialization flattens `spec` back to the top level for clean authoring output.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Type

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


# --- Spec key registry --- #
# Which flat keys belong to which FieldType. For LIST we accept:
#  - "item"  (canonical)
#  - "fields" (authoring sugar for a dict element schema)
SPEC_REGISTRY: Dict[FieldType, tuple[Type[BaseModel], set[str]]] = {
    FieldType.STRING: (StringSpec, {"pattern"}),
    FieldType.NUMBER: (NumberSpec, set()),
    FieldType.BOOLEAN: (BooleanSpec, set()),
    FieldType.ENUM:   (EnumSpec, {"options"}),
    FieldType.DICT:   (DictSpec, {"fields"}),
    FieldType.LIST:   (ListSpec, {"item", "fields"}),
    FieldType.REF:    (RefSpec, {"cardinality", "allow_globs", "must_exist", "base_dir", "extensions"}),
}


# --- Model --- #

class FieldDescriptor(BaseModel):
    """
    One field in a ProcDocs document schema.

    Flat authoring:
      - Common keys: fieldname, fieldtype, required, description, default
      - Type-specific keys live at top-level but are packed into `spec` internally

    Type-specific (live in `spec`; authored flat):
      - string:   pattern
      - enum:     options
      - dict:     fields (list[FieldDescriptor])
      - list:     item (FieldDescriptor)
                  or authoring sugar: fields (list[FieldDescriptor]) for dict elements
                  (default list is list[str] when no item/spec provided)
      - ref:      cardinality, allow_globs, must_exist, base_dir, extensions
    """

    model_config = ConfigDict(validate_assignment=True, extra="forbid")
    _path: str = PrivateAttr(default="")  # excluded from serialization; used for UID

    # Common
    fieldname: str = Field(..., description="Name of the field.")
    fieldtype: FieldType = Field(default=FieldType.STRING, description="Field type.")
    required: bool = Field(default=True, description="Whether this field is required.")
    description: str | None = Field(default=None, description="Human-readable description.")
    default: Any | None = Field(default=None, description="Default value.")

    # Per-type spec (packed/unpacked automatically)
    spec: FieldSpec | None = Field(default=None, description="Type-specific parameters.")

    # --- Pre-parse: pack flat keys into spec --- #
    @model_validator(mode="before")
    @classmethod
    def _pack_flat_spec(cls, data: Any) -> Any:
        """
        Convert flat authoring keys into a typed `spec` based on `fieldtype`.
        Also supports list sugar (`fields` -> synthesized `item` of type dict).
        """
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
                # Render like "['pattern']" to match tests
                allowed_fmt = "[" + ", ".join(repr(k) for k in sorted(allowed_keys)) + "]"
                raise ValueError(
                    f"Unexpected key(s) for fieldtype {ft.value!r}: {sorted(suspicious)}. "
                    f"Allowed: {allowed_fmt}"
                )

        # Synthesize spec from flat keys when provided
        if has_flat and not has_spec:
            # For lists, support authoring sugar: 'fields' instead of 'item'
            if ft == FieldType.LIST and "fields" in present_flat and "item" not in present_flat:
                item_fd = {
                    # Synthesize internal name so FieldDescriptor validation passes
                    "fieldname": f"{(data.get('fieldname') or 'item')}_item",
                    "fieldtype": "dict",
                    "fields": present_flat["fields"],
                }
                present_flat = {"item": item_fd}

            # If list has item but it's missing a fieldname, synthesize one
            if ft == FieldType.LIST and "item" in present_flat:
                it = present_flat["item"]
                if isinstance(it, dict) and "fieldname" not in it:
                    it = {**it, "fieldname": f"{(data.get('fieldname') or 'item')}_item"}
                    present_flat["item"] = it

            synth = {"kind": ft.value, **present_flat}
            # Remove flat keys from top-level and insert 'spec'
            data = {k: v for k, v in data.items() if k not in allowed_keys}
            data["spec"] = synth

        # Minimal list authoring: no item/fields/spec -> default to list[str]
        if not has_flat and not has_spec and ft == FieldType.LIST:
            data["spec"] = {
                "kind": "list",
                "item": {
                    "fieldname": f"{(data.get('fieldname') or 'item')}_item",
                    "fieldtype": "string",
                },
            }

        return data

    # --- Computed UID --- #
    @computed_field  # type: ignore[prop-decorator]
    @property
    def uid(self) -> str:
        """Stable 10-char hash of the descriptor's `_path` (for references/UI)."""
        raw_encode = self._path.encode(C.DEFAULT_TEXT_ENCODING)
        return hashlib.sha1(raw_encode).hexdigest()[:10]

    # --- Validators --- #

    @field_validator("fieldtype", mode="before")
    @classmethod
    def _parse_fieldtype(cls, v: Any) -> FieldType:
        """Coerce incoming values to FieldType (unknowns → INVALID)."""
        return FieldType.parse(v)

    @field_validator("fieldname", mode="before")
    @classmethod
    def _normalize_and_validate_fieldname(cls, v: Any) -> str:
        """
        Strip whitespace, reject reserved names, and enforce FIELDNAME_ALLOWED_RE.
        """
        s = "" if v is None else str(v).strip()
        if not s:
            raise ValueError("The 'fieldname' key is not set")
        if s in C.RESERVED_FIELDNAMES:
            raise ValueError(f"{s!r} is a reserved name and cannot be used")
        if not is_valid_fieldname_pattern(s):
            raise ValueError(
                f"The fieldname {s!r} must match the pattern {C.FIELDNAME_ALLOWED_RE.pattern!r}"
            )
        return s

    @model_validator(mode="after")
    def _post(self) -> "FieldDescriptor":
        """
        Final validation:
        - fieldtype must be known
        - inject defaults for scalar/ref when spec omitted
        - require explicit spec for enum/list/dict
        - ensure spec.kind matches fieldtype
        - extra checks for enum options (non-empty, unique)
        """
        if self.fieldtype == FieldType.INVALID:
            raise ValueError("Unknown fieldtype; valid types are: string, number, boolean, list, dict, enum, ref")

        # Inject defaults for simple types when spec is omitted
        if self.spec is None:
            defaults: Dict[FieldType, FieldSpec] = {
                FieldType.STRING: StringSpec(),
                FieldType.NUMBER: NumberSpec(),
                FieldType.BOOLEAN: BooleanSpec(),
                FieldType.REF:    RefSpec(),
            }
            if self.fieldtype in defaults:
                self.spec = defaults[self.fieldtype]
            else:
                # enum/list/dict require explicit spec (options/children)
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

        return self

    # --- Serializer: flatten spec back to top-level --- #
    @model_serializer(mode="plain")
    def _dump_flat(self) -> Dict[str, Any]:
        """
        Emit flat authoring shape, copying type-specific keys back to the top level.
        - dict:  emits 'fields'
        - list:  emits 'fields' if element is dict; otherwise emits 'item'
                 (hides synthesized item fieldname)
        - others: copies allowed knobs (pattern/options/ref knobs)
        """
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
            item_fd = spec.item

            if item_fd.fieldtype == FieldType.DICT:
                # Author-friendly sugar: emit "fields" only
                dict_spec: DictSpec = item_fd.spec  # type: ignore[assignment]
                flat_spec["fields"] = [fd._dump_flat() for fd in dict_spec.fields]
            else:
                # Scalar/enum/ref element. If it's the default string with no constraints, emit nothing.
                if item_fd.fieldtype == FieldType.STRING:
                    str_spec: StringSpec = item_fd.spec  # type: ignore[assignment]
                    if str_spec.pattern is None:
                        # default list[str] -> no extra keys
                        pass
                    else:
                        # string with pattern -> emit 'item' but hide its fieldname
                        item_dump = item_fd._dump_flat()
                        item_dump.pop("fieldname", None)
                        flat_spec["item"] = item_dump
                else:
                    # number/boolean/enum/ref -> emit 'item' but hide its fieldname
                    item_dump = item_fd._dump_flat()
                    item_dump.pop("fieldname", None)
                    flat_spec["item"] = item_dump

        else:
            # scalar/enums/refs: just copy allowed keys (pattern/options/ref knobs)
            for k in keys:
                if k in spec_dict:
                    flat_spec[k] = spec_dict[k]

        base = {k: v for k, v in base.items() if v is not None}
        return {**base, **flat_spec}


# --- Forward-Ref Resolution --- #
# Resolve forward refs for specs that point to FieldDescriptor
FieldDescriptor.model_rebuild()
rebuild_specs(FieldDescriptor)
