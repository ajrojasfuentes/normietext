"""Public API state, failures, provenance and phase boundaries."""

from dataclasses import replace

import pytest

from normietext import (
    AnnotationKind,
    ExtractionError,
    ExtractionStatus,
    FieldInput,
    FieldStatus,
    InputField,
    JobField,
    JobInputRecord,
    JobTextNormalizer,
    NormalizationPolicy,
    OriginPrecision,
    RecordStatus,
    SourceFormat,
)
from normietext.adapters import convert_source
from normietext.errors import ErrorCode, NormalizationError
from normietext.policy import ResourceLimits
from normietext.stages.encoding import repair_document
from normietext.stages.lexing import lex_document

N = JobTextNormalizer()
D = JobField.JOB_DESCRIPTION


def record_with(first):
    return JobInputRecord(
        tuple([first] + [InputField(f, ExtractionStatus.MISSING) for f in list(JobField)[1:]])
    )


def test_empty_and_missing_and_extraction_failure():
    result = N.normalize_field(FieldInput(D, "🇦"))
    assert result.status is FieldStatus.EMPTY and result.issues
    missing = JobInputRecord(tuple(InputField(f, ExtractionStatus.MISSING) for f in JobField))
    assert N.normalize_record(missing).status is RecordStatus.MISSING
    record = record_with(
        InputField(
            JobField.JOB_TITLE,
            ExtractionStatus.EXTRACTION_ERROR,
            error=ExtractionError("E", "failure"),
        )
    )
    result = N.normalize_record(record)
    assert result.status is RecordStatus.PARTIAL
    assert result.fields[0].input.error.code == "E"
    assert all(f.result is None for f in result.fields)


def test_field_budget_partial_and_strict():
    source = FieldInput(JobField.JOB_TITLE, "x" * 8193)
    record = record_with(InputField(source.field, ExtractionStatus.PRESENT, source))
    result = N.normalize_record(record)
    assert result.status is RecordStatus.PARTIAL
    assert result.fields[0].failure.code is ErrorCode.INPUT_LIMIT_EXCEEDED
    assert result.fields[0].failure.source is source
    with pytest.raises(NormalizationError) as error:
        N.normalize_record(record, strict=True)
    assert error.value.code is ErrorCode.INPUT_LIMIT_EXCEEDED


def test_record_aggregate_budget_is_atomic():
    normalizer = JobTextNormalizer(NormalizationPolicy(limits=ResourceLimits(record=2)))
    source = FieldInput(JobField.JOB_TITLE, "abc")
    with pytest.raises(NormalizationError) as error:
        normalizer.normalize_record(
            record_with(InputField(source.field, ExtractionStatus.PRESENT, source))
        )
    assert error.value.code is ErrorCode.INPUT_LIMIT_EXCEEDED


def test_typed_reentry_does_not_repair_or_reinterpret(monkeypatch):
    source = FieldInput(D, "&amp;lt;b&amp;gt;", SourceFormat.HTML_ESCAPED_TEXT)
    parsed = convert_source(source)
    repaired = repair_document(parsed)
    lexical = lex_document(repaired)
    expected = N.canonicalize(lexical)
    import ftfy

    monkeypatch.setattr(
        ftfy, "fix_encoding_and_explain", lambda *a, **kw: pytest.fail("second repair")
    )
    assert N.canonicalize(repaired) == expected
    assert N.canonicalize(lexical) == expected
    assert N.canonicalize(expected) is expected
    assert expected.text == "&lt;b&gt;"
    other = JobTextNormalizer(NormalizationPolicy(limits=ResourceLimits(record=100)))
    with pytest.raises(NormalizationError) as error:
        other.canonicalize(expected)
    assert error.value.code is ErrorCode.POLICY_MISMATCH


def test_repeated_generated_tokens_exact_spans_and_raw_origins():
    raw = "a\u200b\u0301 🇨🇷 a\u200b\u0301 🇨🇷 [flag:CR]"
    result = N.normalize_field(FieldInput(D, raw))
    flags = [a for a in result.annotations if a.kind is AnnotationKind.EMOJI_REGION]
    assert [a.span.start for a in flags] == [2, 14]
    assert [raw[a.origin.span.start : a.origin.span.end] for a in flags] == ["🇨🇷", "🇨🇷"]
    assert all(a.origin.precision is OriginPrecision.EXACT for a in flags)
    assert len({a.id for a in flags}) == 2
    html = N.normalize_field(FieldInput(D, "<p>🇨🇷 🇨🇷</p>", SourceFormat.HTML_FRAGMENT))
    assert all(a.origin.precision is OriginPrecision.FIELD for a in html.annotations)
    assert [a.span.start for a in html.annotations] == [0, 10]


def test_protected_spacing_and_code_blocks():
    result = N.normalize_field(FieldInput(D, "```\n  a\u200b\uff0fb🚀c\n```"))
    assert result.text == "```\na\uff0fb c\n```"
    assert any(b.kind == "code" for b in result.blocks)
    assert any(i.code == "PROTECTED_SPAN_MODIFIED" for i in result.issues)


def test_canonical_revalidation_rejects_invalid_text():
    result = N.normalize_field(FieldInput(D, "a"))
    with pytest.raises(NormalizationError) as error:
        N.canonicalize(replace(result, text="a\u200b"))
    assert error.value.code is ErrorCode.OUTPUT_INVARIANT_FAILED


@pytest.mark.parametrize("parent_span", [(0, 0), (1, 3), (0, 2)])
def test_canonical_revalidation_rejects_child_outside_parent(parent_span):
    from normietext import BlockKind, Span

    result = N.normalize_field(FieldInput(D, "<div><p>ABC</p></div>", SourceFormat.HTML_FRAGMENT))
    blocks = tuple(
        replace(b, span=Span(*parent_span)) if b.kind is BlockKind.CONTAINER else b
        for b in result.blocks
    )
    with pytest.raises(NormalizationError) as error:
        N.canonicalize(replace(result, blocks=blocks))
    assert error.value.code is ErrorCode.OUTPUT_INVARIANT_FAILED


@pytest.mark.parametrize("value", [None, {}, "raw"])
def test_invalid_document(value):
    with pytest.raises(NormalizationError) as error:
        N.canonicalize(value)
    assert error.value.code is ErrorCode.INVALID_TYPE


def test_generated_annotation_payload_and_marker_revalidated():
    result = N.normalize_field(FieldInput(D, "🇨🇷"))
    from normietext import FrozenMap

    bad = replace(result.annotations[0], payload=FrozenMap.from_mapping({"value": "XX"}))
    with pytest.raises(NormalizationError) as error:
        N.canonicalize(replace(result, annotations=(bad,)))
    assert error.value.code is ErrorCode.OUTPUT_INVARIANT_FAILED
    result = N.normalize_field(FieldInput(D, "1. A"))
    bad_blocks = tuple(replace(b, ordinal=2) if b.kind == "list_item" else b for b in result.blocks)
    with pytest.raises(NormalizationError) as error:
        N.canonicalize(replace(result, blocks=bad_blocks))
    assert error.value.code is ErrorCode.OUTPUT_INVARIANT_FAILED


def test_nested_list_and_continuation_envelopes():
    result = N.normalize_field(FieldInput(D, "• A\n\t• B\n\t  continued\n• C"))
    blocks = {b.id: b for b in result.blocks}
    child = next(b for b in result.blocks if b.kind == "list_item" and b.depth == 1)
    continuation = next(b for b in result.blocks if b.metadata.get("continuation"))
    assert continuation.parent_id == child.id
    assert child.span.start <= continuation.span.start < continuation.span.end <= child.span.end
    assert blocks[child.parent_id].span.end >= child.span.end


def test_list_depth_budget():
    n = JobTextNormalizer(NormalizationPolicy(limits=ResourceLimits(structural_depth=2)))
    with pytest.raises(NormalizationError) as error:
        n.normalize_field(FieldInput(D, "• A\n  • B\n    • C"))
    assert error.value.code is ErrorCode.RESOURCE_LIMIT_EXCEEDED


@pytest.mark.parametrize(
    ("contents", "expected_text"),
    [
        (["A", "", "C"], "A | | C"),
        (["A", "", "", "B"], "A | | | B"),
        (["", "", ""], "| |"),
        (["", "", "B"], "| | B"),
        (["A", "", ""], "A | |"),
    ],
)
def test_empty_cells_remain_empty_and_nonempty_spans_exclude_separators(contents, expected_text):
    raw = "<table><tr>" + "".join(f"<td>{v}</td>" for v in contents) + "</tr></table>"
    result = N.normalize_field(FieldInput(D, raw, SourceFormat.HTML_FRAGMENT))
    assert result.text == expected_text
    assert result.source.raw == raw
    cells = sorted((b for b in result.blocks if b.kind == "table_cell"), key=lambda b: b.column)
    assert [result.text[b.span.start : b.span.end] for b in cells] == contents
    assert [(b.row, b.column) for b in cells] == [(0, i) for i in range(len(contents))]
    assert N.canonicalize(result) is result


def test_unclassified_selector_and_isolated_marker_variant():
    assert N.clean_text("🛸️\u0301", D) == "🛸\u0301"
    assert N.clean_text("👉️", D) == ""


def test_output_budget_blocks_expanding_converted_document():
    from normietext import (
        AlignmentSegment,
        Block,
        BlockKind,
        Origin,
        ParsedDocument,
        SourceEvidence,
        Span,
    )

    source = SourceEvidence.from_input(FieldInput(D, "x"))
    origin = Origin(OriginPrecision.EXACT, Span(0, 1))
    parsed = ParsedDocument(
        source,
        "x",
        blocks=tuple(
            Block(str(i), BlockKind.LIST_ITEM, Span(0, 0), origin, list_id="L", origin_tag="li")
            for i in range(600)
        ),
        alignment=(AlignmentSegment(Span(0, 1), origin, True),),
    )
    with pytest.raises(NormalizationError) as error:
        N.canonicalize(parsed)
    assert error.value.code is ErrorCode.OUTPUT_LIMIT_EXCEEDED


@pytest.mark.parametrize(
    ("raw", "expected", "items"),
    [
        ('<ol start="3"><li></li><li></li></ol>', "3.\n4.", ["3.", "4."]),
        ('<ol start="3"><li><ol><li>B</li></ol></li></ol>', "3.\n1. B", ["3.\n1. B", "1. B"]),
    ],
)
def test_empty_and_nested_only_dom_items_have_distinct_marker_spans(raw, expected, items):
    result = N.normalize_field(FieldInput(D, raw, SourceFormat.HTML_FRAGMENT))
    assert result.text == expected
    blocks = sorted(
        (b for b in result.blocks if b.kind == "list_item"), key=lambda b: (b.span.start, b.depth)
    )
    assert [result.text[b.span.start : b.span.end] for b in blocks] == items
