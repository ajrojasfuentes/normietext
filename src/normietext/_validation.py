"""Strict, cached validation for immutable domain dataclasses (no coercion)."""

from dataclasses import fields
from types import UnionType
from typing import Any, get_args, get_origin, get_type_hints

from normietext.errors import ErrorCode, ModelValidationError


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ModelValidationError(ErrorCode.INVALID_MODEL, message)


def valid_text(value: str) -> bool:
    return not any(0xD800 <= ord(char) <= 0xDFFF for char in value)


_TYPE_HINTS: dict[type[object], dict[str, Any]] = {}


def _hints(cls: type[object]) -> dict[str, Any]:
    if cls not in _TYPE_HINTS:
        _TYPE_HINTS[cls] = get_type_hints(cls)
    return _TYPE_HINTS[cls]


def _matches(value: object, annotation: Any) -> bool:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is UnionType:
        return any(_matches(value, item) for item in args)
    if origin is tuple:
        if type(value) is not tuple:
            return False
        if len(args) == 2 and args[1] is Ellipsis:
            return all(_matches(item, args[0]) for item in value)
        return len(value) == len(args) and all(
            _matches(item, kind) for item, kind in zip(value, args, strict=True)
        )
    if annotation in (str, int, bool, float, type(None)):
        return type(value) is annotation
    return isinstance(value, annotation)


class Validated:
    """Subclasses must use frozen dataclasses and immutable field types only."""

    __slots__ = ()

    def __post_init__(self) -> None:
        hints = _hints(type(self))
        for field in fields(self):  # type: ignore[arg-type]
            value = getattr(self, field.name)
            require(_matches(value, hints[field.name]), f"Invalid type for {field.name}")
            if isinstance(value, str):
                require(valid_text(value), f"Invalid Unicode in {field.name}")
