"""Ingestion-side source preservation. No storage callbacks occur in transformations."""

from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Protocol

from normietext.errors import (
    ErrorCode,
    InputValidationError,
    NormalizationError,
    SourceRecoveryError,
)
from normietext.models import FieldInput, JobField, SourceEvidence, SourceFormat
from normietext.policy import ResourceLimits

_DEFAULT_LIMITS = ResourceLimits()


@dataclass(frozen=True, slots=True, repr=False)
class RejectedInput:
    """Local error envelope, deliberately excluded from canonical JSON (may contain surrogates)."""

    field: object
    value: object
    source_format: object
    source_ref: str | None
    source_adapter_version: str | None


class RejectedInputError(InputValidationError):
    def __init__(self, code: ErrorCode, rejected: RejectedInput) -> None:
        self.rejected = rejected
        super().__init__(code, "Input rejected; original retained in local ingestion envelope")


def prepare_input(
    value: object,
    field: object,
    *,
    source_format: object = SourceFormat.PLAIN_TEXT,
    source_ref: str | None = None,
    source_adapter_version: str | None = None,
    limits: ResourceLimits = _DEFAULT_LIMITS,
) -> FieldInput:
    """Check scalar type/length before Unicode scans or any expensive processing."""
    rejected = RejectedInput(field, value, source_format, source_ref, source_adapter_version)
    code = None
    if not isinstance(field, JobField):
        code = ErrorCode.INVALID_FIELD
    elif not isinstance(source_format, SourceFormat):
        code = ErrorCode.INVALID_FORMAT
    elif type(value) is not str:
        code = ErrorCode.INVALID_TYPE
    elif len(value) > limits.for_field(field):
        code = ErrorCode.INPUT_LIMIT_EXCEEDED
    if code is not None:
        raise RejectedInputError(code, rejected)
    assert isinstance(value, str) and isinstance(field, JobField)
    assert isinstance(source_format, SourceFormat)
    try:
        return FieldInput(field, value, source_format, source_ref, source_adapter_version)
    except NormalizationError as exc:
        raise RejectedInputError(exc.code, rejected) from None


class SourceStore(Protocol):
    """Persist durably before return, use immutable refs and read exact envelopes.

    Implementations belong to the host. They may perform I/O here, never in the
    normalization path. Read-back proves identity now, not future durability.
    """

    def persist(self, source: FieldInput) -> str: ...

    def read(self, reference: str) -> FieldInput: ...


def recover_source(evidence: SourceEvidence, store: SourceStore | None = None) -> FieldInput:
    if evidence.raw is not None:
        source = FieldInput(
            evidence.field,
            evidence.raw,
            evidence.source_format,
            evidence.source_ref,
            evidence.source_adapter_version,
        )
    else:
        if store is None or not evidence.source_ref or not evidence.source_sha256:
            raise SourceRecoveryError(
                ErrorCode.SOURCE_UNAVAILABLE, "Verified source store required"
            )
        try:
            source = store.read(evidence.source_ref)
        except Exception as exc:
            raise SourceRecoveryError(ErrorCode.SOURCE_UNAVAILABLE, "Source read failed") from exc
        if not isinstance(source, FieldInput):
            raise SourceRecoveryError(
                ErrorCode.SOURCE_MISMATCH, "Store returned an invalid envelope"
            )
    if (
        source.field is not evidence.field
        or source.source_format is not evidence.source_format
        or source.source_adapter_version != evidence.source_adapter_version
        or source.source_ref != evidence.source_ref
        or len(source.value) != evidence.source_length
        or (
            evidence.source_sha256 is not None
            and sha256(source.value.encode("utf-8")).hexdigest() != evidence.source_sha256
        )
    ):
        raise SourceRecoveryError(ErrorCode.SOURCE_MISMATCH, "Recovered source identity mismatch")
    return source


def persist_source(source: FieldInput, store: SourceStore) -> SourceEvidence:
    """Explicit ingestion operation; remove raw only after successful read-back verification."""
    try:
        reference = store.persist(source)
    except Exception as exc:
        raise SourceRecoveryError(
            ErrorCode.SOURCE_UNAVAILABLE, "Source persistence failed"
        ) from exc
    if not isinstance(reference, str) or not reference:
        raise SourceRecoveryError(ErrorCode.SOURCE_MISMATCH, "Store returned invalid reference")
    evidence = replace(SourceEvidence.from_input(source), raw=None, source_ref=reference)
    recovered = recover_source(evidence, store)
    if recovered.value != source.value:
        raise SourceRecoveryError(ErrorCode.SOURCE_MISMATCH, "Source read-back differs")
    return evidence
