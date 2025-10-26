#!/usr/bin/env python3
"""
Purpose:
    Implements the FieldDescriptor model for ProcDocs schemas, handling
    validation, normalization, packing/unpacking of type-specific specs,
    and flat serialization.
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

        ft = cls._fd_parse_fieldtype(data.get("fieldtype"))
        spec_model, allowed_keys = cls._fd_spec_model_and_keys(ft)
        if not spec_model:
            return data  # unknown type handled later

        flat = cls._fd_present_flat(data, allowed_keys)
        has_flat = bool(flat)
        has_spec = cls._fd_has_spec_dict(data)
        cls._fd_raise_if_mixed_spec(has_flat, has_spec)
        cls._fd_raise_if_stray_keys(data, ft, allowed_keys)

        if has_flat and not has_spec:
            parent = data.get("fieldname")
            flat = cls._fd_synthesize_list_sugar(ft, flat, parent)
            flat = cls._fd_ensure_item_fieldname(ft, flat, parent)
            synth = {"kind": ft.value, **flat}
            data = cls._fd_strip_flat_keys(data, allowed_keys)
            data["spec"] = synth

        if not has_flat and not has_spec and ft == FieldType.LIST:
            data["spec"] = cls._fd_default_list_spec(data.get("fieldname"))

        return data

    # --- Computed UID --- #
    @computed_field  # type: ignore[prop-decorator]
    @property
    def uid(self) -> str:
        """Stable 10-char hash of the descriptor's `_path` (for references/UI)."""
        raw_encode = self._path.encode(C.DEFAULT_TEXT_ENCODING)
        return hashlib.sha256(raw_encode).hexdigest()[:10]

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

        self._inject_defaults_if_missing()
        self._ensure_spec_kind_matches()
        self._validate_enum_options()

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
        base = {k: v for k, v in self._dump_base().items() if v is not None}

        if self.fieldtype == FieldType.DICT:
            flat_spec = self._dump_dict_spec()

        elif self.fieldtype == FieldType.LIST:
            flat_spec = self._dump_list_spec()

        else:
            flat_spec = self._dump_scalar_like()

        return {**base, **flat_spec}

    # --- Pack Flat Spec Helpers --- #
    @staticmethod
    def _fd_parse_fieldtype(raw_ft) -> FieldType:
        return FieldType.parse(raw_ft) if raw_ft is not None else FieldType.STRING

    @staticmethod
    def _fd_spec_model_and_keys(ft: FieldType):
        return SPEC_REGISTRY.get(ft, (None, set()))

    @staticmethod
    def _fd_present_flat(data: dict, allowed_keys: set[str]) -> dict:
        return {k: v for k, v in data.items() if k in allowed_keys}

    @staticmethod
    def _fd_has_spec_dict(data: dict) -> bool:
        return isinstance(data.get("spec"), dict)

    @staticmethod
    def _fd_raise_if_mixed_spec(has_flat: bool, has_spec: bool) -> None:
        if has_flat and has_spec:
            raise ValueError("Provide either flat type-specific keys or 'spec', not both")

    @staticmethod
    def _fd_raise_if_stray_keys(data: dict, ft: FieldType, allowed_keys: set[str]) -> None:
        stray = {k for k in data.keys() if k not in (_fd_common_keys() | allowed_keys)}
        if not stray:
            return
        suspicious = stray & _fd_other_type_keys(ft)
        if suspicious:
            allowed_fmt = "[" + ", ".join(repr(k) for k in sorted(allowed_keys)) + "]"
            raise ValueError(
                f"Unexpected key(s) for fieldtype {ft.value!r}: {sorted(suspicious)}. "
                f"Allowed: {allowed_fmt}"
            )

    @staticmethod
    def _fd_synthesize_list_sugar(ft: FieldType, flat: dict, parent_name: str | None) -> dict:
        """Support authoring sugar 'fields' instead of 'item' for list-of-dicts."""
        if ft != FieldType.LIST or "fields" not in flat or "item" in flat:
            return flat
        item_fd = {
            "fieldname": f"{(parent_name or 'item')}_item",
            "fieldtype": "dict",
            "fields": flat["fields"],
        }
        return {"item": item_fd}

    @staticmethod
    def _fd_ensure_item_fieldname(ft: FieldType, flat: dict, parent_name: str | None) -> dict:
        """Ensure list item dict has a fieldname (synthesized if missing)."""
        if ft != FieldType.LIST or "item" not in flat:
            return flat
        it = flat["item"]
        if isinstance(it, dict) and "fieldname" not in it:
            flat = {**flat, "item": {**it, "fieldname": f"{(parent_name or 'item')}_item"}}
        return flat

    @staticmethod
    def _fd_strip_flat_keys(data: dict, allowed_keys: set[str]) -> dict:
        return {k: v for k, v in data.items() if k not in allowed_keys}

    @staticmethod
    def _fd_default_list_spec(parent_name: str | None) -> dict:
        return {
            "kind": "list",
            "item": {
                "fieldname": f"{(parent_name or 'item')}_item",
                "fieldtype": "string",
            },
        }

    # --- Dump Flat Helpers --- #
    def _dump_base(self) -> Dict[str, Any]:
        return {
            "fieldname": self.fieldname,
            "fieldtype": self.fieldtype.value,
            "required": self.required,
            "description": self.description,
            "default": self.default,
        }

    def _dump_dict_spec(self) -> Dict[str, Any]:
        spec: DictSpec = self.spec  # type: ignore[assignment]
        return {"fields": [fd._dump_flat() for fd in spec.fields]}

    def _dump_list_item_as_fields_or_item(self, item_fd) -> Dict[str, Any]:
        # list of dicts → emit "fields"
        if item_fd.fieldtype == FieldType.DICT:
            dict_spec: DictSpec = item_fd.spec  # type: ignore[assignment]
            return {"fields": [fd._dump_flat() for fd in dict_spec.fields]}

        # scalar/enum/ref/string-with-pattern → emit "item" (hide fieldname)
        if item_fd.fieldtype == FieldType.STRING:
            str_spec: StringSpec = item_fd.spec  # type: ignore[assignment]
            if str_spec.pattern is None:
                return {}  # default list[str] — nothing to emit

        item_dump = item_fd._dump_flat()
        item_dump.pop("fieldname", None)
        return {"item": item_dump}

    def _dump_list_spec(self) -> Dict[str, Any]:
        spec: ListSpec = self.spec  # type: ignore[assignment]
        return self._dump_list_item_as_fields_or_item(spec.item)

    def _dump_scalar_like(self) -> Dict[str, Any]:
        _, keys = SPEC_REGISTRY[self.fieldtype]
        spec_dict = self.spec.model_dump() if self.spec else {}
        return {k: spec_dict[k] for k in keys if k in spec_dict}

    # --- Post Helpers --- #
    def _inject_defaults_if_missing(self) -> None:
        if self.spec is not None:
            return
        defaults: Dict[FieldType, FieldSpec] = {
            FieldType.STRING: StringSpec(),
            FieldType.NUMBER: NumberSpec(),
            FieldType.BOOLEAN: BooleanSpec(),
            FieldType.REF:    RefSpec(),
        }
        if self.fieldtype in defaults:
            self.spec = defaults[self.fieldtype]
            return
        raise ValueError(f"{self.fieldtype.value} requires a 'spec' block")

    def _ensure_spec_kind_matches(self) -> None:
        if getattr(self.spec, "kind", None) != self.fieldtype.value:
            raise ValueError(f"'spec.kind' ({self.spec.kind}) does not match fieldtype '{self.fieldtype.value}'")

    def _validate_enum_options(self) -> None:
        if self.fieldtype != FieldType.ENUM:
            return
        opts = [str(o) for o in self.spec.options]  # type: ignore[attr-defined]
        if any(s.strip() == "" for s in opts):
            raise ValueError("ENUM 'options' must not contain empty strings")
        if len(set(opts)) != len(opts):
            raise ValueError("ENUM 'options' contain duplicates")


def _fd_common_keys() -> set[str]:
    return {"fieldname", "fieldtype", "required", "description", "default", "spec"}


def _fd_other_type_keys(this_ft: FieldType) -> set[str]:
    keys: set[str] = set()
    for t, (_, ks) in SPEC_REGISTRY.items():
        if t != this_ft:
            keys |= ks
    return keys


# --- Forward-Ref Resolution --- #
# Resolve forward refs for specs that point to FieldDescriptor
FieldDescriptor.model_rebuild()
rebuild_specs(FieldDescriptor)
