"""Literal conversion, including explicitly unknown source format."""

from dataclasses import replace

from normietext.adapters._common import DEFAULT_LIMITS, initial, literal_document
from normietext.errors import ErrorCode, InputValidationError
from normietext.models import (
    FieldInput,
    Issue,
    IssueCode,
    Origin,
    OriginPrecision,
    ParsedDocument,
    SourceFormat,
)
from normietext.policy import ResourceLimits


def convert(source: FieldInput, limits: ResourceLimits = DEFAULT_LIMITS) -> ParsedDocument:
    tracked = initial(source, limits)
    if source.source_format not in (SourceFormat.PLAIN_TEXT, SourceFormat.UNKNOWN):
        raise InputValidationError(
            ErrorCode.INVALID_FORMAT, "Literal adapter requires literal format"
        )
    document = literal_document(tracked, limits)
    if source.source_format is SourceFormat.UNKNOWN:
        document = replace(
            document,
            issues=(
                Issue(
                    IssueCode.SOURCE_FORMAT_UNKNOWN, "format.unknown", Origin(OriginPrecision.FIELD)
                ),
            ),
        )
    return document
