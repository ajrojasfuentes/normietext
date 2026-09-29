"""One explained origin repair after format conversion, preserving initial provenance."""

from dataclasses import replace
from itertools import pairwise

import ftfy

from normietext.adapters import tracked_document
from normietext.errors import (
    ErrorCode,
    InputValidationError,
    PolicyMismatchError,
    ResourceLimitError,
)
from normietext.manifest import create_manifest
from normietext.models import (
    EncodingRepair,
    FieldInput,
    FrozenMap,
    Issue,
    IssueCode,
    OriginPrecision,
    ParsedDocument,
    RepairedDocument,
    SourceEvidence,
    Span,
)
from normietext.policy import NormalizationPolicy
from normietext.provenance import Replacement, TrackedText
from normietext.serialization import canonical_bytes

_DEFAULT_POLICY = NormalizationPolicy()


def repair_document(
    document: ParsedDocument, policy: NormalizationPolicy = _DEFAULT_POLICY
) -> RepairedDocument:
    """Repair logical structural/line units once; never parse, compact or remove controls."""
    if not isinstance(document, ParsedDocument):
        raise InputValidationError(ErrorCode.INVALID_TYPE, "Expected converted document")
    if document.source.source_length > policy.limits.for_field(document.source.field):
        raise InputValidationError(ErrorCode.INPUT_LIMIT_EXCEEDED, "Source exceeds field budget")
    if len(document.text) > policy.limits.output_limit(document.source.source_length):
        raise ResourceLimitError(
            ErrorCode.OUTPUT_LIMIT_EXCEEDED, "Intermediate text exceeds budget"
        )
    manifest = create_manifest(policy)
    if isinstance(document, RepairedDocument):
        if canonical_bytes(document.manifest) != canonical_bytes(manifest):
            raise PolicyMismatchError(ErrorCode.POLICY_MISMATCH, "Reprocess the original source")
        document.__post_init__()
        return document
    tracked = tracked_document(document)
    # Adapters must have captured literal line separators before ftfy sees them.
    if any(char in document.text for char in "\r\x85\u2028\u2029\v\f"):
        raise InputValidationError(ErrorCode.INVALID_MODEL, "Line tokenization required first")
    cuts = {0, len(document.text)}
    for block in document.blocks:
        cuts.update((block.span.start, block.span.end))
    for annotation in document.annotations:
        if annotation.span is not None:
            cuts.update((annotation.span.start, annotation.span.end))
    for index, char in enumerate(document.text):
        if char == "\n":
            cuts.update((index, index + 1))
    changes = []
    explanations = []
    options = policy.encoding
    for start, end in pairwise(sorted(cuts)):
        unit = document.text[start:end]
        if not unit or unit == "\n":
            continue
        fixed = ftfy.fix_encoding_and_explain(
            unit,
            restore_byte_a0=options.restore_byte_a0,
            replace_lossy_sequences=options.replace_lossy_sequences,
            decode_inconsistent_utf8=options.decode_inconsistent_utf8,
            fix_c1_controls=options.fix_c1_controls,
        )
        if fixed.text != unit:
            changes.append(Replacement(Span(start, end), fixed.text, "encoding.fix_encoding"))
            explanations.append(tuple((step[0], step[1]) for step in fixed.explanation or ()))
    repaired = tracked.replace(tuple(changes), limits=policy.limits)
    # This temporary map translates converted offsets to repaired offsets. It is
    # never exposed as raw evidence; repaired.alignment still points to initial raw.
    local = TrackedText.from_source(
        SourceEvidence.from_input(FieldInput(document.source.field, document.text))
    ).replace(tuple(changes), limits=policy.limits)
    repairs = []
    issues = list(document.issues)
    for change, explanation, edit in zip(
        changes, explanations, repaired.edits[len(tracked.edits) :], strict=True
    ):
        span = local.alignment.project(change.span)
        repairs.append(EncodingRepair(change.span, span, edit.origin, edit.id, explanation))
        if edit.origin.precision is OriginPrecision.SEGMENT:
            issues.append(
                Issue(
                    IssueCode.ORIGIN_PRECISION_REDUCED,
                    "encoding.fix_encoding",
                    edit.origin,
                    FrozenMap.from_mapping({"reason": "repair_has_no_character_map"}),
                )
            )
    for index, char in enumerate(repaired.text):
        if char == "\ufffd":
            issues.append(
                Issue(
                    IssueCode.REPLACEMENT_CHARACTER_PRESENT,
                    "encoding.replacement_character",
                    repaired.alignment.origin_for(Span(index, index + 1)),
                )
            )
    return RepairedDocument(
        source=document.source,
        text=repaired.text,
        blocks=tuple(
            replace(block, span=local.alignment.project(block.span)) for block in document.blocks
        ),
        associations=document.associations,
        annotations=tuple(
            replace(item, span=local.alignment.project(item.span))
            if item.span is not None
            else item
            for item in document.annotations
        ),
        edits=repaired.edits,
        issues=tuple(issues),
        alignment=repaired.alignment.segments,
        manifest=manifest,
        repairs=tuple(repairs),
        converted_length=len(document.text),
    )
