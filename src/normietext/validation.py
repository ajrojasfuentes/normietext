"""Resource gates and canonical-envelope validation; no normalization or source-store calls."""

import json
import unicodedata
from bisect import bisect_right
from functools import lru_cache
from importlib.resources import files

from normietext.errors import (
    ErrorCode,
    InputValidationError,
    ModelValidationError,
    OutputInvariantError,
    PolicyMismatchError,
    ResourceLimitError,
)
from normietext.manifest import create_manifest, policy_hash
from normietext.models import (
    Annotation,
    AnnotationKind,
    Association,
    Block,
    BlockKind,
    Edit,
    FieldInput,
    Issue,
    JobInputRecord,
    Manifest,
    NormalizedField,
)
from normietext.policy import NormalizationPolicy, ResourceLimits
from normietext.serialization import canonical_bytes

_DEFAULT_LIMITS = ResourceLimits()

_DEFAULT_POLICY = NormalizationPolicy()


def validate_input(source: FieldInput, limits: ResourceLimits = _DEFAULT_LIMITS) -> FieldInput:
    if not isinstance(source, FieldInput):
        raise InputValidationError(ErrorCode.INVALID_TYPE, "Expected FieldInput")
    if len(source.value) > limits.for_field(source.field):
        raise InputValidationError(ErrorCode.INPUT_LIMIT_EXCEEDED, "Field input exceeds budget")
    source.__post_init__()
    return source


def validate_record(
    record: JobInputRecord, limits: ResourceLimits = _DEFAULT_LIMITS
) -> JobInputRecord:
    record.__post_init__()
    total = sum(len(item.source.value) for item in record.fields if item.source is not None)
    if total > limits.record:
        raise InputValidationError(ErrorCode.INPUT_LIMIT_EXCEEDED, "Record input exceeds budget")
    for item in record.fields:
        if item.source is not None:
            validate_input(item.source, limits)
    return record


@lru_cache(maxsize=1)
def _forbidden() -> tuple[tuple[int, ...], tuple[tuple[int, int], ...]]:
    data = json.loads(files("normietext").joinpath("data/unicode_properties.json").read_bytes())
    ranges = sorted(
        tuple(pair)
        for name in ("Cf", "Cc", "Default_Ignorable_Code_Point")
        for pair in data["entries"][name]
    )
    merged: list[tuple[int, int]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1] = merged[-1][0], max(merged[-1][1], end)
        else:
            merged.append((start, end))
    return tuple(start for start, _ in merged), tuple(merged)


def validate_text(text: str, *, compact: bool) -> None:
    starts, ranges = _forbidden()
    invalid = not unicodedata.is_normalized("NFC", text)
    invalid |= text != text.strip(" \n") or "  " in text or "\n\n\n" in text
    invalid |= any(line != line.strip(" ") for line in text.split("\n"))
    invalid |= compact and "\n" in text
    for char in text:
        point = ord(char)
        index = bisect_right(starts, point) - 1
        invalid |= 0xD800 <= point <= 0xDFFF or point == 0x2800
        invalid |= char != "\n" and index >= 0 and point < ranges[index][1]
        invalid |= char.isspace() and char not in " \n"
    if invalid:
        raise OutputInvariantError(ErrorCode.OUTPUT_INVARIANT_FAILED, "Invalid canonical text")


def validate_canonical(
    document: NormalizedField,
    policy: NormalizationPolicy = _DEFAULT_POLICY,
    *,
    expected_manifest: Manifest | None = None,
) -> NormalizedField:
    """Check compatible phase, environment, structure and base invariants; return the same object.

    Reentry validates representation; it never repeats source recognition or repair.
    expected_manifest must come from trusted initialization, never the input document.
    """
    if not isinstance(document, NormalizedField):
        raise PolicyMismatchError(ErrorCode.POLICY_MISMATCH, "Expected canonical phase")
    expected = create_manifest(policy) if expected_manifest is None else expected_manifest
    if expected.policy_hash != policy_hash(policy) or canonical_bytes(
        document.manifest
    ) != canonical_bytes(expected):
        raise PolicyMismatchError(
            ErrorCode.POLICY_MISMATCH, "Reprocess original source under this environment"
        )
    if document.source.source_length > policy.limits.for_field(document.field):
        raise InputValidationError(ErrorCode.INPUT_LIMIT_EXCEEDED, "Source exceeds field budget")
    if len(document.text) > policy.limits.output_limit(document.source.source_length):
        raise ResourceLimitError(ErrorCode.OUTPUT_LIMIT_EXCEEDED, "Output exceeds expansion budget")
    try:
        # Constructors are not trusted as a substitute for revalidation at the boundary.
        document.source.__post_init__()
        document.manifest.__post_init__()
        entries: tuple[Block | Association | Annotation | Edit | Issue, ...] = (
            *document.blocks,
            *document.associations,
            *document.annotations,
            *document.edits,
            *document.issues,
        )
        for item in entries:
            item.__post_init__()
            item.origin.__post_init__()
            if item.origin.span is not None:
                item.origin.span.__post_init__()
            span = getattr(item, "span", None)
            if span is not None:
                span.__post_init__()
        document.__post_init__()
        if document.source.raw is None and not document.source.source_sha256:
            raise ModelValidationError(ErrorCode.INVALID_MODEL, "External source requires digest")
    except ModelValidationError as exc:
        raise OutputInvariantError(
            ErrorCode.OUTPUT_INVARIANT_FAILED, "Invalid canonical references"
        ) from exc
    validate_text(document.text, compact=document.field.value in policy.output.compact_fields)
    _validate_representation(document)
    return document


def _validate_representation(document: NormalizedField) -> None:
    from normietext.stages.lexing import _tables

    hints, regions, _ = _tables()
    hint_values = set(hints.values())
    region_values = {code for kind, code, _ in regions.values() if kind == "region"}
    subdivision_values = {code for kind, code, _ in regions.values() if kind != "region"}
    for annotation in document.annotations:
        value = annotation.payload.get("value")
        expected = None
        valid = True
        if annotation.kind is AnnotationKind.EMOJI_HINT:
            expected, valid = f"[emoji:{value}]", value in hint_values
        elif annotation.kind is AnnotationKind.EMOJI_REGION:
            expected, valid = f"[flag:{value}]", value in region_values
        elif annotation.kind is AnnotationKind.EMOJI_SUBDIVISION:
            expected, valid = f"[flag-subdivision:{value}]", value in subdivision_values
        if expected is not None and (not valid or annotation.rendered_token != expected):
            raise OutputInvariantError(
                ErrorCode.OUTPUT_INVARIANT_FAILED, "Invalid generated annotation"
            )
    by_id = {block.id: block for block in document.blocks}
    for block in document.blocks:
        if block.parent_id is not None:
            parent = by_id[block.parent_id]
            if not parent.span.start <= block.span.start <= block.span.end <= parent.span.end:
                raise OutputInvariantError(
                    ErrorCode.OUTPUT_INVARIANT_FAILED, "Child outside canonical parent"
                )
        if block.kind is not BlockKind.LIST_ITEM:
            continue
        text = document.text[block.span.start : block.span.end]
        prefix = "-" if block.ordinal is None else f"{block.ordinal}."
        if (
            text != prefix
            and not text.startswith(prefix + " ")
            and not text.startswith(prefix + "\n")
        ):
            raise OutputInvariantError(ErrorCode.OUTPUT_INVARIANT_FAILED, "Invalid list projection")
