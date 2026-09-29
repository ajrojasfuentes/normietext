"""F4 repair acceptance, independently of the final normalizer."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from normietext import (
    ErrorCode,
    FieldInput,
    IssueCode,
    JobField,
    NormalizationPolicy,
    OriginPrecision,
    SourceFormat,
    Span,
)
from normietext.adapters import convert_source, tracked_document
from normietext.errors import InputValidationError, PolicyMismatchError
from normietext.serialization import canonical_bytes
from normietext.stages.encoding import repair_document
from normietext.stages.lexing import lex_document

ROOT = Path(__file__).parents[1] / "fixtures/lexical"
CASES = json.loads((ROOT / "cases.json").read_bytes())["cases"]


def test_f4_fixture_schema():
    schema = json.loads((ROOT / "schema.json").read_bytes())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads((ROOT / "cases.json").read_bytes()))


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_repaired_and_lexical_fixture(case):
    converted = convert_source(
        FieldInput(JobField.JOB_DESCRIPTION, case["raw"], SourceFormat(case["format"]))
    )
    repaired = repair_document(converted)
    lexed = lex_document(repaired)
    assert repaired.text == case["repaired_text"]
    assert len(repaired.repairs) == case["repairs"]
    assert repaired.source.raw == case["raw"]
    assert repaired.phase.value == "repaired" and lexed.phase.value == "lexed"
    assert [
        [repaired.text[t.span.start : t.span.end], t.kind.value, t.action.value]
        for t in lexed.tokens
        if t.kind.value not in ("text", "line_break")
    ] == case["special_tokens"]
    assert [
        [repaired.text[p.span.start : p.span.end], p.kind.value] for p in lexed.protections
    ] == case["protections"]
    assert {issue.code.value for issue in lexed.issues} == set(case["issues"])
    assert repair_document(repaired) is repaired
    assert lex_document(lexed) is lexed


def test_repair_once_explanation_and_provenance_reach_initial_escaped_source(monkeypatch):
    converted = convert_source(
        FieldInput(JobField.JOB_DESCRIPTION, "Jos&#195;&#169;", SourceFormat.HTML_ESCAPED_TEXT)
    )
    repaired = repair_document(converted)
    assert repaired.text == "José"
    assert repaired.repairs[0].explanation == (("encode", "latin-1"), ("decode", "utf-8"))
    assert repaired.repairs[0].origin.span == Span(0, len(converted.source.raw))
    assert repaired.repairs[0].origin.precision is OriginPrecision.SEGMENT
    assert repaired.edits[-1].rule_id == "encoding.fix_encoding"

    def forbidden(*args, **kwargs):
        raise AssertionError("Origin repair cannot run twice")

    monkeypatch.setattr("normietext.stages.encoding.ftfy.fix_encoding_and_explain", forbidden)
    assert repair_document(repaired) is repaired
    with pytest.raises(InputValidationError):
        convert_source(repaired)
    policy = NormalizationPolicy()
    different = replace(policy, limits=replace(policy.limits, job_title=100))
    with pytest.raises(PolicyMismatchError):
        repair_document(repaired, different)
    with pytest.raises(PolicyMismatchError):
        lex_document(repaired, different)


def test_structural_units_and_annotation_boundaries_preserve_relationships():
    raw = '<dl><dt>JosÃ©</dt><dd><a href="https://example.com">don\x92t</a> rest</dd></dl>'
    converted = convert_source(
        FieldInput(JobField.JOB_CRITERIA_LIST, raw, SourceFormat.HTML_FRAGMENT)
    )
    repaired = repair_document(converted)
    assert repaired.text == "José\ndon\u2019t rest"
    assert repaired.associations == converted.associations
    assert [b.id for b in repaired.blocks] == [b.id for b in converted.blocks]
    link = repaired.annotations[0]
    assert repaired.text[link.span.start : link.span.end] == "don\u2019t"
    assert all(r.origin.precision is OriginPrecision.FIELD for r in repaired.repairs)
    assert all(s.origin.precision is OriginPrecision.FIELD for s in repaired.alignment)
    assert tracked_document(repaired).source.raw == raw


@pytest.mark.parametrize("field", tuple(JobField))
def test_nel_precedes_ftfy_and_f4_never_compacts_or_removes_controls(field):
    source = FieldInput(field, "  a\x85 b\x01\x81\t")
    repaired = repair_document(convert_source(source))
    assert repaired.text == "  a\n b\x01\x81\t"
    assert not repaired.repairs  # ftfy may explain a no-op C1 step; it is not an edit.
    assert [e.rule_id for e in repaired.edits] == ["format.line_break"]


def test_replacement_character_diagnostic_not_duplicated_on_reentry():
    document = repair_document(convert_source(FieldInput(JobField.JOB_TITLE, "�")))
    assert [i.code for i in document.issues] == [IssueCode.REPLACEMENT_CHARACTER_PRESENT]
    assert canonical_bytes(document) == canonical_bytes(repair_document(document))


def test_repair_rejects_wrong_phase_and_missing_alignment():
    from normietext import ParsedDocument

    with pytest.raises(InputValidationError):
        repair_document("JosÃ©")
    source = convert_source(FieldInput(JobField.JOB_TITLE, "x"))
    from normietext.errors import ModelValidationError

    with pytest.raises(ModelValidationError):
        repair_document(ParsedDocument(source.source, "x"))
    with pytest.raises(InputValidationError) as caught:
        repair_document(replace(source, text="\r"))
    assert caught.value.code is ErrorCode.INVALID_MODEL


def test_repair_checks_resource_budgets_before_ftfy(monkeypatch):
    from normietext.errors import ResourceLimitError

    source = convert_source(FieldInput(JobField.JOB_TITLE, "abc"))

    def forbidden(*args, **kwargs):
        raise AssertionError("Budget gate must precede repair")

    monkeypatch.setattr("normietext.stages.encoding.ftfy.fix_encoding_and_explain", forbidden)
    policy = NormalizationPolicy()
    with pytest.raises(InputValidationError) as caught:
        repair_document(source, replace(policy, limits=replace(policy.limits, job_title=2)))
    assert caught.value.code is ErrorCode.INPUT_LIMIT_EXCEEDED
    from normietext import ParsedDocument

    with pytest.raises(ResourceLimitError) as caught:
        repair_document(ParsedDocument(source.source, "x" * 1025))
    assert caught.value.code is ErrorCode.OUTPUT_LIMIT_EXCEEDED


def test_repair_spans_and_explanations_are_deeply_immutable_and_validated():
    from dataclasses import FrozenInstanceError

    from normietext.errors import ModelValidationError

    repaired = repair_document(convert_source(FieldInput(JobField.JOB_TITLE, "JosÃ©")))
    with pytest.raises(FrozenInstanceError):
        repaired.repairs[0].explanation = ()
    with pytest.raises(ModelValidationError):
        replace(repaired, converted_length=1)
    with pytest.raises(ModelValidationError):
        replace(repaired, repairs=(replace(repaired.repairs[0], span=Span(0, 1)),))
