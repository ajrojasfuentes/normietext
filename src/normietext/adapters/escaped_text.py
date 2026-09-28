"""Decode exactly one declared HTML character-reference layer; output stays literal."""

import html
import re

from normietext.adapters._common import DEFAULT_LIMITS, initial, literal_document
from normietext.errors import ErrorCode, InputValidationError
from normietext.models import FieldInput, ParsedDocument, SourceFormat, Span
from normietext.policy import ResourceLimits
from normietext.provenance import Replacement

# CPython html.unescape's documented HTML5 behavior, matching original references
# as units so expansion/contraction composes to their exact original intervals.
_CHARREF = re.compile(r"&(#[0-9]+;?|#[xX][0-9a-fA-F]+;?|[^\t\n\f <&#;]{1,32};?)")


def convert(source: FieldInput, limits: ResourceLimits = DEFAULT_LIMITS) -> ParsedDocument:
    tracked = initial(source, limits)
    if source.source_format is not SourceFormat.HTML_ESCAPED_TEXT:
        raise InputValidationError(
            ErrorCode.INVALID_FORMAT, "Escaped adapter requires declared format"
        )
    changes = tuple(
        Replacement(
            Span(m.start(), m.end()), html.unescape(m.group()), "format.unescape_once", True
        )
        for m in _CHARREF.finditer(tracked.text)
    )
    return literal_document(tracked.replace(changes, limits=limits), limits)
