"""Public local, deterministic field/record API with typed canonical reentry."""

from dataclasses import dataclass, field

from normietext.adapters import convert_source
from normietext.errors import ErrorCode, InputValidationError, NormalizationError
from normietext.models import (
    FieldFailure,
    FieldInput,
    FieldOutcome,
    JobField,
    JobInputRecord,
    LexedDocument,
    NormalizedField,
    NormalizedJobRecord,
    ParsedDocument,
    SourceFormat,
)
from normietext.policy import NormalizationPolicy
from normietext.stages.encoding import repair_document
from normietext.stages.lexing import lex_document
from normietext.stages.rendering import render_document
from normietext.validation import validate_canonical


@dataclass(frozen=True, slots=True)
class JobTextNormalizer:
    policy: NormalizationPolicy = field(default_factory=NormalizationPolicy)

    def __post_init__(self) -> None:
        if not isinstance(self.policy, NormalizationPolicy):
            raise InputValidationError(ErrorCode.INVALID_POLICY, "Expected NormalizationPolicy")
        self.policy.__post_init__()

    def normalize_field(self, source: FieldInput) -> NormalizedField:
        return self.canonicalize(convert_source(source, limits=self.policy.limits))

    def canonicalize(
        self, document: ParsedDocument | LexedDocument | NormalizedField
    ) -> NormalizedField:
        if isinstance(document, NormalizedField):
            return validate_canonical(document, self.policy)
        if isinstance(document, LexedDocument):
            lexical = lex_document(document, self.policy)
        elif isinstance(document, ParsedDocument):
            lexical = lex_document(repair_document(document, self.policy), self.policy)
        else:
            raise InputValidationError(ErrorCode.INVALID_TYPE, "Expected a typed document")
        return validate_canonical(render_document(lexical, self.policy), self.policy)

    def clean_text(
        self, text: str, field: JobField, *, source_format: SourceFormat = SourceFormat.PLAIN_TEXT
    ) -> str:
        return self.normalize_field(FieldInput(field, text, source_format)).text

    def normalize_record(
        self, record: JobInputRecord, *, strict: bool = False
    ) -> NormalizedJobRecord:
        if not isinstance(record, JobInputRecord) or type(strict) is not bool:
            raise InputValidationError(
                ErrorCode.INVALID_RECORD, "Expected record and boolean strict option"
            )
        record.__post_init__()
        total = sum(len(item.source.value) for item in record.fields if item.source is not None)
        if total > self.policy.limits.record:
            raise InputValidationError(
                ErrorCode.INPUT_LIMIT_EXCEEDED, "Record input exceeds budget"
            )
        outcomes = []
        for item in record.fields:
            if item.source is None:
                outcomes.append(FieldOutcome(item))
                continue
            try:
                outcomes.append(FieldOutcome(item, self.normalize_field(item.source)))
            except NormalizationError as exc:
                if strict:
                    raise
                outcomes.append(
                    FieldOutcome(item, failure=FieldFailure(item.source, exc.code, str(exc)))
                )
        return NormalizedJobRecord(tuple(outcomes))
