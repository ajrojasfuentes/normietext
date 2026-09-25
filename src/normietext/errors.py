"""Typed failures; operational failures never masquerade as normalized fields."""

from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_TYPE = "INVALID_TYPE"
    INVALID_FIELD = "INVALID_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_UNICODE = "INVALID_UNICODE"
    INVALID_RECORD = "INVALID_RECORD"
    INVALID_MODEL = "INVALID_MODEL"
    INVALID_POLICY = "INVALID_POLICY"
    INPUT_LIMIT_EXCEEDED = "INPUT_LIMIT_EXCEEDED"
    HTML_PARSE_FAILED = "HTML_PARSE_FAILED"
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
    REGEX_TIMEOUT = "REGEX_TIMEOUT"
    OUTPUT_LIMIT_EXCEEDED = "OUTPUT_LIMIT_EXCEEDED"
    OUTPUT_INVARIANT_FAILED = "OUTPUT_INVARIANT_FAILED"
    POLICY_MISMATCH = "POLICY_MISMATCH"


class NormalizationError(ValueError):
    """A stable code and a diagnostic message, without implicitly logging source text."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        if not isinstance(code, ErrorCode):
            raise TypeError("code must be ErrorCode")
        self.code = code
        super().__init__(message)


class InputValidationError(NormalizationError):
    """Invalid field input or record envelope."""


class ModelValidationError(NormalizationError):
    """An inconsistent domain model."""


class PolicyValidationError(NormalizationError):
    """An unknown option or inconsistent policy."""


class ResourceLimitError(NormalizationError):
    """An operational resource budget was exceeded."""


class OutputInvariantError(NormalizationError):
    """The implementation produced an invalid canonical result."""


class PolicyMismatchError(NormalizationError):
    """Reprocessing the recoverable source is required."""
