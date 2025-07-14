#!/usr/bin/env python3

from typing import Optional, List, Dict, Any, Callable

from procdocs.core.utils import is_strict_semver
from procdocs.core.validation import ValidationResult


class BaseMetadata:
    """
    Base class for document and schema metadata.
    Stores document type, version, and format version, with validation.
    Additionally stores user-defined metadata information as attributes.
    """

    def __init__(self) -> None:
        self._format_version: Optional[str] = None
        self._user_defined: Dict[str, Any] = {}
        self._check_declared_attributes_exist(self._required)
        self._check_declared_attributes_exist(self._derived_attributes)

    @property
    def format_version(self) -> Optional[str]:
        return self._format_version

    @format_version.setter
    def format_version(self, value: str) -> None:
        if not is_strict_semver(str(value)):
            raise ValueError(f"Invalid format version: '{value}'")
        self._format_version = value

    def to_dict(self) -> Dict[str, str]:
        base = {
            "format_version": self.format_version,
        }
        derived_attrs = self._derived_attributes()
        for key in derived_attrs:
            base[key] = getattr(self, key)
        for key in self._user_defined:
            base[key] = getattr(self, key)
        return base

    @classmethod
    def from_dict(cls, data: Dict, strict: bool = True) -> "BaseMetadata":
        """
        Create a metadata instance from a dict with optional key mapping.
        """
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
        """
        Raise an error or collect validation issues if required fields are missing.
        """
        collector = collector or ValidationResult()
        collector = self._validate_required_fields_are_set(collector=collector, strict=strict)
        collector = self._validate_format_version(collector=collector, strict=strict)
        return collector
    
    def _validate_required_fields_are_set(self, collector: Optional[ValidationResult] = None, strict: bool = True) -> ValidationResult:
        collector = collector or ValidationResult()
        required_attrs = self._required()
        missing = [attr for attr in required_attrs if getattr(self, attr, None) is None]
        if missing:
            msg = "Missing required metadata fields: " + ", ".join(f"'{m}'" for m in missing)
            collector.report(msg, strict, ValueError)
        return collector
    
    def _validate_format_version(self, collector: Optional[ValidationResult] = None, strict: bool = True) -> ValidationResult:
        collector = collector or ValidationResult()
        if self.format_version and not is_strict_semver(str(self.format_version)):
            msg = f"Invalid format version: '{self.format_version}'"
            collector.report(msg, strict, ValueError)
        return collector

    def _add_user_field(self, key: str, data: Any) -> None:
        self._user_defined[key] = data

    def _required(self) -> List[str]:
        raise NotImplementedError("Must be implemented by the derived class")

    def _derived_attributes(self) -> List[str]:
        raise NotImplementedError("Must be implemented by the derived class")
    
    def _check_declared_attributes_exist(self, attr_func: Callable[[], list[str]]) -> None:
        """
        Calls the given function to retrieve a list of attribute names and checks
        whether they are valid attributes on the object. Raises an error if any are missing.
        """
        attr_list = attr_func()
        missing = [a for a in attr_list if not hasattr(self, a)]
        if missing:
            raise AttributeError(
                f"{attr_func.__name__}() returned invalid attribute(s): {', '.join(missing)}"
            )

    def __getattr__(self, name: str) -> Any:
        if name in self._user_defined:
            return self._user_defined[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
