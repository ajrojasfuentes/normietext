"""Converted-stage acceptance; no claims about the final normalizer corpus."""

import json
import socket
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from normietext import (
    AnnotationKind,
    BlockKind,
    ErrorCode,
    FieldInput,
    FormatConversionError,
    InputValidationError,
    IssueCode,
    JobField,
    OriginPrecision,
    ResourceLimitError,
    ResourceLimits,
    SourceFormat,
    Span,
)
from normietext.adapters import convert_source, html_fragment, tracked_document
from normietext.serialization import canonical_bytes

ROOT = Path(__file__).resolve().parents[1] / "fixtures/adaptation"
CASES = json.loads((ROOT / "cases.json").read_bytes())


def html(raw, **limits):
    return convert_source(
        FieldInput(JobField.JOB_DESCRIPTION, raw, SourceFormat.HTML_FRAGMENT),
        limits=ResourceLimits(**limits),
    )


def fragments(document, kind):
    return [document.text[b.span.start : b.span.end] for b in document.blocks if b.kind is kind]


def test_adaptation_fixture_schema():
    schema = json.loads((ROOT / "schema.json").read_bytes())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(CASES)
    assert len({case["id"] for case in CASES["cases"]}) == len(CASES["cases"])


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda c: c["id"])
def test_converted_stage_fixtures(case):
    source = FieldInput(JobField(case["field"]), case["raw"], SourceFormat(case["source_format"]))
    result = convert_source(source)
    assert result.text == case["expected_text"]
    assert result.phase.value == "converted"
    assert result.source.raw == source.value
    assert canonical_bytes(result) == canonical_bytes(convert_source(source))
    tracked = tracked_document(result)
    assert tracked.text == result.text and tracked.source == result.source
    by_id = {b.id: b for b in result.blocks}
    for block in result.blocks:
        assert block.span.end <= len(result.text)
        if block.parent_id:
            parent = by_id[block.parent_id]
            assert parent.span.start <= block.span.start <= block.span.end <= parent.span.end
    if source.source_format is SourceFormat.UNKNOWN:
        assert [i.code for i in result.issues] == [IssueCode.SOURCE_FORMAT_UNKNOWN]


def test_literal_and_entity_alignment_never_reinterpret_converted_output():
    source = FieldInput(JobField.JOB_TITLE, "&lt;b&gt;X&lt;/b&gt;", SourceFormat.HTML_ESCAPED_TEXT)
    result = convert_source(source)
    assert result.text == "<b>X</b>" and all(b.kind is BlockKind.LINE for b in result.blocks)
    mapped = tracked_document(result).alignment.origin_for(Span(0, 1))
    assert mapped.precision is OriginPrecision.EXACT and mapped.span == Span(0, 4)
    with pytest.raises(InputValidationError):
        convert_source(result)
    assert tracked_document(result).text == "<b>X</b>"
    literal = convert_source(FieldInput(JobField.JOB_TITLE, "a\r\n  b"))
    assert tracked_document(literal).alignment.origin_for(Span(1, 2)).span == Span(1, 3)
    assert fragments(literal, BlockKind.LINE) == ["a", "  b"]


def test_preserve_whitespace_only_nodes_and_combining_sequences():
    result = html("<p><b>A</b>   <i>B</i> a\u0301 💰\u200d</p>")
    assert result.text == "A   B a\u0301 💰\u200d"
    assert all(segment.origin.precision is OriginPrecision.FIELD for segment in result.alignment)
    assert IssueCode.ORIGIN_PRECISION_REDUCED in {i.code for i in result.issues}


def test_ordered_lists_reversed_values_nested_styles_and_no_prefix_rewriting():
    result = html(
        '<ol reversed type="I"><li>one<ul><li>nested</li></ul></li>'
        '<li value="7" type="a">7. seven</li><li>six</li></ol>'
    )
    items = [b for b in result.blocks if b.kind is BlockKind.LIST_ITEM]
    assert [b.ordinal for b in items] == [3, None, 7, 6]
    assert [b.depth for b in items] == [0, 1, 0, 0]
    assert items[1].list_id != items[0].list_id == items[2].list_id
    assert items[2].metadata["list_style"] == "a"
    assert "7. seven" in result.text
    assert not result.associations
    assert [
        b.ordinal
        for b in html('<ol start="-1"><li>A</li><li value="0">B</li></ol>').blocks
        if b.kind is BlockKind.LIST_ITEM
    ] == [-1, 0]


def test_invalid_attributes_report_deterministic_fallbacks():
    result = html(
        '<ol reversed start="bad" type="q"><li value="x">A</li><li>B</li></ol>'
        '<table><tr><td colspan="no" rowspan="-1">X</td></tr></table>'
    )
    assert [b.ordinal for b in result.blocks if b.kind is BlockKind.LIST_ITEM] == [2, 1]
    assert sum(i.code is IssueCode.INVALID_HTML_ATTRIBUTE for i in result.issues) == 5
    cell = next(b for b in result.blocks if b.kind is BlockKind.TABLE_CELL)
    assert cell.rowspan == cell.colspan == 1
    assert (
        next(
            b
            for b in html('<ol start="' + "9" * 100 + '"><li>X</li></ol>').blocks
            if b.kind is BlockKind.LIST_ITEM
        ).ordinal
        == 1
    )


def test_tables_coordinates_empty_cells_groups_caption_and_nested_tables():
    result = html(
        '<table><caption>Pay</caption><thead><tr><th colspan="2">Band</th></tr></thead>'
        '<tbody><tr><td rowspan="2">CR</td><td></td></tr><tr><td>USD</td></tr></tbody>'
        "<tfoot><tr><td>Total</td><td>2</td></tr></tfoot></table>"
    )
    cells = [b for b in result.blocks if b.kind is BlockKind.TABLE_CELL]
    assert [(b.row, b.column, b.rowspan, b.colspan) for b in cells] == [
        (0, 0, 1, 2),
        (1, 0, 2, 1),
        (1, 1, 1, 1),
        (2, 1, 1, 1),
        (3, 0, 1, 1),
        (3, 1, 1, 1),
    ]
    assert cells[0].header and cells[2].span.start == cells[2].span.end
    assert len({b.metadata["table_id"] for b in cells}) == 1
    assert any(b.origin_tag == "caption" for b in result.blocks)
    zero = html(
        '<table><tbody><tr><td rowspan="0">A</td><td>B</td></tr><tr><td>C</td></tr></tbody></table>'
    )
    assert next(b for b in zero.blocks if b.kind is BlockKind.TABLE_CELL).rowspan == 2
    nested = html("<table><tr><td>A<table><tr><td>B</td></tr></table></td><td>C</td></tr></table>")
    cells = [b for b in nested.blocks if b.kind is BlockKind.TABLE_CELL]
    assert [b.column for b in cells] == [0, 0, 1]
    assert (
        cells[0].metadata["table_id"]
        == cells[2].metadata["table_id"]
        != cells[1].metadata["table_id"]
    )


def test_description_lists_multiplicity_missing_members_and_no_typographic_inference():
    result = html(
        "<dl><dd>orphan</dd><div><dt>A</dt><dt>B</dt><dd>C</dd><dd>D</dd></div><dt>alone</dt></dl>"
    )
    assert [(len(a.term_ids), len(a.definition_ids)) for a in result.associations] == [
        (0, 1),
        (2, 2),
        (1, 0),
    ]
    assert all(a.source_contract == "html.dl/1.0.0" for a in result.associations)
    assert not html("<li><h3>Type</h3><strong>Full-time</strong></li>").associations


def test_representation_annotations_are_visible_and_urls_never_requested(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("Network must not be used")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    result = html(
        '<a href="https://example.invalid/?a=1&amp;b=2">Apply</a>'
        '<img alt="Remote &amp; hybrid" src="https://example.invalid/image">'
        "<s>Old</s><del>Gone</del>x<sup>2</sup>H<sub>2</sub>O"
    )
    assert [a.kind for a in result.annotations] == [
        AnnotationKind.LINK,
        AnnotationKind.ALT_TEXT,
        AnnotationKind.STRUCK_TEXT,
        AnnotationKind.STRUCK_TEXT,
        AnnotationKind.SUPERSCRIPT,
        AnnotationKind.SUBSCRIPT,
    ]
    assert result.annotations[0].payload["href"] == "https://example.invalid/?a=1&b=2"
    assert [result.text[a.span.start : a.span.end] for a in result.annotations] == [
        "Apply",
        "Remote & hybrid",
        "Old",
        "Gone",
        "2",
        "2",
    ]
    private = tmp_path / "private.txt"
    private.write_text("PRIVATE_TEST_SENTINEL")
    entity = html(f'<!DOCTYPE html [<!ENTITY secret SYSTEM "{private.as_uri()}">]><p>&secret;</p>')
    assert "PRIVATE_TEST_SENTINEL" not in entity.text
    html('<!DOCTYPE html SYSTEM "https://example.invalid/external.dtd"><p>Safe</p>')


def test_parser_settings_no_fallback_and_available_recovery_diagnostics(monkeypatch):
    calls = []
    real = html_fragment._LocalBuilder.parser_for

    def observed(self, encoding):
        calls.append(encoding)
        return real(self, encoding)

    monkeypatch.setattr(html_fragment._LocalBuilder, "parser_for", observed)
    recovered = html("<p>x</div>")
    assert len(calls) == 1 and recovered.text == "x"
    assert any(issue.code is IssueCode.HTML_RECOVERY for issue in recovered.issues)

    def fail(self, encoding):
        calls.append(encoding)
        raise ValueError("backend unavailable")

    monkeypatch.setattr(html_fragment._LocalBuilder, "parser_for", fail)
    with pytest.raises(FormatConversionError) as caught:
        html("<p>hello</p>")
    assert caught.value.code is ErrorCode.HTML_PARSE_FAILED and len(calls) == 2


def test_input_nodes_depth_and_output_limits_block_partial_results(monkeypatch):
    with pytest.raises(ResourceLimitError):
        html("<p>x</p>", html_nodes=3)
    assert html("<div><p>x</p></div>", structural_depth=2).text == "x"
    with pytest.raises(ResourceLimitError):
        html("<div><div><p>x</p></div></div>", structural_depth=2)
    with pytest.raises(ResourceLimitError):
        html('<table><tr><td colspan="1000">x</td></tr></table>', html_nodes=20)

    def must_not_parse(*args, **kwargs):
        raise AssertionError("Size must be checked before parser invocation")

    monkeypatch.setattr(html_fragment, "_parse", must_not_parse)
    with pytest.raises(InputValidationError) as caught:
        html("x" * 11, job_description=10)
    assert caught.value.code is ErrorCode.INPUT_LIMIT_EXCEEDED


def test_typed_converted_alignment_is_serialized_and_revalidated():
    from normietext import AlignmentSegment, Origin
    from normietext.errors import ModelValidationError

    result = convert_source(FieldInput(JobField.JOB_TITLE, "abc"))
    data = json.loads(canonical_bytes(result))
    assert data["alignment"][0]["linear"] is True
    with pytest.raises(ModelValidationError):
        replace(
            result,
            alignment=(
                AlignmentSegment(Span(0, 2), Origin(OriginPrecision.EXACT, Span(0, 2)), True),
            ),
        )


@pytest.mark.parametrize("field", tuple(JobField))
def test_adaptation_does_not_compact_fields_or_infer_lists(field):
    source = FieldInput(field, "\n  1. A\n\n  2. B\n")
    result = convert_source(source)
    assert result.text == source.value
    assert all(block.kind is BlockKind.LINE for block in result.blocks)


def test_parser_factory_explicit_security_options(monkeypatch):
    from types import SimpleNamespace

    actual_import = html_fragment.importlib.import_module
    actual_etree = actual_import("lxml.etree")
    observed = []

    def factory(**kwargs):
        observed.append(kwargs)
        return actual_etree.HTMLParser(**kwargs)

    def module(name):
        return SimpleNamespace(HTMLParser=factory) if name == "lxml.etree" else actual_import(name)

    monkeypatch.setattr(html_fragment.importlib, "import_module", module)
    assert html("<p>x</p>").text == "x"
    assert len(observed) == 1
    assert observed[0]["no_network"] is True
    assert observed[0]["huge_tree"] is False
    assert observed[0]["decompress"] is False
    assert observed[0]["target"] is not None


def test_row_groups_reset_occupancy_and_inline_code_keeps_context():
    doc = html(
        '<table><thead><tr><th rowspan="3">Header</th></tr></thead>'
        "<tbody><tr><td>Body</td></tr></tbody></table>"
    )
    assert [b.column for b in doc.blocks if b.kind is BlockKind.TABLE_CELL] == [0, 0]
    code = html("Use <code>--flag  2. x</code> here")
    assert code.text == "Use --flag  2. x here"
    assert fragments(code, BlockKind.CODE) == ["--flag  2. x"]


def test_escaping_does_not_invent_references_across_original_matches():
    raw = "&amp;amp; &#38;lt; &notit; &#xD800;"
    doc = convert_source(FieldInput(JobField.JOB_DESCRIPTION, raw, SourceFormat.HTML_ESCAPED_TEXT))
    assert doc.text == "&amp; &lt; ¬it; �"
    assert all(edit.rule_id == "format.unescape_once" for edit in doc.edits)


def test_dl_explicit_group_boundaries_do_not_fill_missing_members():
    doc = html("<dl><div><dt>A</dt></div><div><dd>B</dd></div></dl>")
    assert [(len(a.term_ids), len(a.definition_ids)) for a in doc.associations] == [(1, 0), (0, 1)]


def test_host_recursion_failure_is_typed_and_does_not_publish_partial_document(monkeypatch):
    def exhausted(*args, **kwargs):
        raise RecursionError

    monkeypatch.setattr(html_fragment._Projection, "walk", exhausted)
    with pytest.raises(ResourceLimitError) as caught:
        html("<p>data</p>")
    assert caught.value.code is ErrorCode.RESOURCE_LIMIT_EXCEEDED
