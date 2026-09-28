"""Explicit, one-time format conversion. Results are converted, not normalized."""

from normietext.adapters import escaped_text, html_fragment, plain_text
from normietext.adapters._common import DEFAULT_LIMITS, tracked_document
from normietext.errors import ErrorCode, InputValidationError
from normietext.models import FieldInput, ParsedDocument, SourceFormat
from normietext.policy import ResourceLimits

__all__ = ["convert_source", "tracked_document"]


def convert_source(
    source: FieldInput, *, limits: ResourceLimits = DEFAULT_LIMITS
) -> ParsedDocument:
    if not isinstance(source, FieldInput):
        raise InputValidationError(
            ErrorCode.INVALID_TYPE, "Expected fresh FieldInput, not converted text"
        )
    if source.source_format is SourceFormat.HTML_FRAGMENT:
        return html_fragment.convert(source, limits)
    if source.source_format is SourceFormat.HTML_ESCAPED_TEXT:
        return escaped_text.convert(source, limits)
    return plain_text.convert(source, limits)
