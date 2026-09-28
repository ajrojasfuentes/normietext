"""Shared conversion boundary and line-tokenization; no repair or canonical rendering."""

import re

from normietext.errors import ErrorCode, InputValidationError
from normietext.models import Block, BlockKind, FieldInput, ParsedDocument, SourceEvidence, Span
from normietext.policy import ResourceLimits
from normietext.provenance import Alignment, Replacement, TrackedText, stable_id
from normietext.validation import validate_input

DEFAULT_LIMITS = ResourceLimits()
LINE_BREAK = re.compile(r"\r\n|[\r\x85\u2028\u2029\v\f]")


def initial(source: FieldInput, limits: ResourceLimits) -> TrackedText:
    if not isinstance(source, FieldInput):
        raise InputValidationError(ErrorCode.INVALID_TYPE, "Conversion requires fresh FieldInput")
    validate_input(source, limits)
    return TrackedText.from_source(SourceEvidence.from_input(source))


def tokenize_lines(tracked: TrackedText, limits: ResourceLimits) -> TrackedText:
    changes = tuple(
        Replacement(Span(m.start(), m.end()), "\n", "format.line_break", True)
        for m in LINE_BREAK.finditer(tracked.text)
    )
    return tracked.replace(changes, limits=limits)


def literal_document(tracked: TrackedText, limits: ResourceLimits) -> ParsedDocument:
    tracked = tokenize_lines(tracked, limits)
    blocks = []
    start = 0
    # str.split preserves empty and final lines; no heading/list inference here.
    for occurrence, line in enumerate(tracked.text.split("\n")):
        span = Span(start, start + len(line))
        origin = tracked.alignment.origin_for(span)
        blocks.append(
            Block(
                stable_id("block", tracked.source, "format.line", origin, occurrence=occurrence),
                BlockKind.LINE,
                span,
                origin,
            )
        )
        start = span.end + 1
    return ParsedDocument(
        tracked.source,
        tracked.text,
        blocks=tuple(blocks),
        edits=tracked.edits,
        alignment=tracked.alignment.segments,
    )


def tracked_document(document: ParsedDocument) -> TrackedText:
    """Pass converted text/alignment to later stages without decoding its source again."""
    return TrackedText(
        document.source,
        document.text,
        Alignment(document.source.source_length, len(document.text), document.alignment),
        document.edits,
    )
