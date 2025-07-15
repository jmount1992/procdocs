#!/usr/bin/env python3

from functools import cached_property
from typing import Optional, List, Dict, Any

from procdocs.core.base.base_validator import BaseValidator
from procdocs.core.validation import ValidationResult


class Base(metaclass=BaseValidator):
    _ATTRIBUTES: List[str] = ["_user_defined"]
    _REQUIRED: List[str] = []

    def __init__(self) -> None:
        # Dynamically create fields based on attributes
        for attr in self._attributes:
            print(attr)
            setattr(self, attr, None)
        self._user_defined: Dict[str, Any] = {}

    @cached_property
    def attributes(self) -> List[str]:
        """Gets the list of object-defined attributes (public names)"""
        return self._collect_class_attrs("_ATTRIBUTES", private=False)

    @cached_property
    def _attributes(self) -> List[str]:
        """Gets the list of object-defined attributes (private names)"""
        return self._collect_class_attrs("_ATTRIBUTES", private=True)

    @cached_property
    def required(self) -> List[str]:
        """Gets the list of required attributes (public names)"""
        return self._collect_class_attrs("_REQUIRED", private=False)

    @cached_property
    def _required(self) -> List[str]:
        """Gets the list of required attributes (rprivate names)"""
        return self._collect_class_attrs("_REQUIRED", private=True)

    @property
    def user_defined(self) -> List[str]:
        """Gets the list of user defined attributes"""
        return list(self._user_defined.keys())

    def to_dict(self) -> Dict[str, Any]:
        base = {}
        for key in self.attributes:
            if key != "user_defined":
                base[key] = getattr(self, key)
        for key in self.user_defined:
            base[key] = getattr(self, key)
        return base

    @classmethod
    def from_dict(cls, data: Dict, strict: bool = True) -> "Base":
        obj = cls()
        for key, val in data.items():
            norm_key = key.replace('-', '_')
            norm_key = norm_key if strict else f"_{norm_key}"
            if hasattr(obj, norm_key):
                setattr(obj, norm_key, val)
            else:
                obj._add_user_field(key, val)
        obj.validate(strict=strict)
        return obj

    def validate(self, collector: Optional[ValidationResult] = None, strict: bool = True) -> ValidationResult:
        collector = collector or ValidationResult()
        collector = self._validate_required_fields_are_set(collector=collector, strict=strict)
        collector = self._validate_additional(collector=collector, strict=strict)
        return collector

    def _validate_additional(self, collector: ValidationResult, strict: bool) -> ValidationResult:
        raise NotImplementedError("Derived class must implement _validate_additional()")

    def _validate_required_fields_are_set(self, collector: Optional[ValidationResult] = None, strict: bool = True) -> ValidationResult:
        collector = collector or ValidationResult()
        required_attrs = self.required
        missing = [attr for attr in required_attrs if getattr(self, attr, None) is None]
        if missing:
            msg = "Missing required metadata fields: " + ", ".join(f"'{m}'" for m in missing)
            collector.report(msg, strict, ValueError)
        return collector

    def _add_user_field(self, key: str, data: Any) -> None:
        self._user_defined[key] = data

    def __getattr__(self, name: str) -> Any:
        if name in self._user_defined:
            return self._user_defined[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def _collect_class_attrs(self, attr_name: str, private: bool = True) -> List[str]:
        seen = []
        for cls in reversed(type(self).__mro__):
            if hasattr(cls, attr_name):
                seen.extend(getattr(cls, attr_name))
        unique = list(dict.fromkeys(seen))  # remove duplicates, preserve order
        if private:
            return unique
        return [name.lstrip("_") for name in unique]
