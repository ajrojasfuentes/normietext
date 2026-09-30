"""Consumers retain evidence and abstain instead of inventing semantic facts."""

import json
from decimal import Decimal

import pytest
from jsonschema import Draft202012Validator

from evaluation.evidence import DerivedView, collect, collect_record, decimal_amount, evidence_bytes
from evaluation.quality import FIXTURES, evaluate, span_errors
from normietext import (
    ExtractionError,
    ExtractionStatus,
    FieldInput,
    InputField,
    JobField,
    JobInputRecord,
    JobTextNormalizer,
    OriginPrecision,
    SourceFormat,
    Span,
)

N = JobTextNormalizer()
D = JobField.JOB_DESCRIPTION


def normalized(raw, fmt=SourceFormat.PLAIN_TEXT):
    return N.normalize_field(FieldInput(D, raw, fmt))


def record(raw):
    return N.normalize_record(
        JobInputRecord(
            tuple(
                InputField(f, ExtractionStatus.PRESENT, FieldInput(f, raw))
                if f is D
                else InputField(f, ExtractionStatus.MISSING)
                for f in JobField
            )
        )
    )


def test_quality_schema_and_gate():
    for data, schema in [
        ("cases.json", "schema.json"),
        ("integral_evidence.json", "integral_evidence.schema.json"),
    ]:
        definition = json.loads((FIXTURES / "quality" / schema).read_bytes())
        Draft202012Validator.check_schema(definition)
        Draft202012Validator(definition).validate(
            json.loads((FIXTURES / "quality" / data).read_bytes())
        )
    report = evaluate()
    assert report["passed"], report["failures"]
    assert report["list_metrics"]["predicted"] == 30
    assert report["list_metrics"].get("fp", 0) == 0
    assert report["mandatory_negatives"]
    assert all(item["false_positives"] == 0 for item in report["mandatory_negatives"])
    assert all(item["cases"] > 0 for item in report["ablations"].values())
    assert report["integral"]["missing"] == []


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("4500.25", Decimal("4500.25")),
        ("0.004", Decimal("0.004")),
        ("1,234.56", Decimal("1234.56")),
        ("1.234,56", Decimal("1234.56")),
        ("2,400,000", Decimal("2400000")),
        ("55k", Decimal("55000")),
        ("1,200", None),
        ("4.500", None),
        ("1,2,3", None),
        ("123456789012345678901234567890.12", Decimal("123456789012345678901234567890.12")),
    ],
)
def test_decimal_exact_or_explicit_abstention(raw, expected):
    assert decimal_amount(raw) == expected
    if expected is not None:
        assert json.loads(evidence_bytes(expected)) == format(expected, "f")


@pytest.mark.parametrize(
    "raw",
    [
        "Salary USD 4500",
        "Salary $4500/month",
        "Salary USD 4,500/month",
        "Salary USD 4500/month or USD 60000/year",
        "Salary USD 4500/month if eligible",
        "Budget USD 4500/year",
        "Salary if eligible:\nUSD 4500/month",
        "Bonus USD 1000/year",
        "Cost USD 0.004/request",
    ],
)
def test_insufficient_or_alternative_salary_is_null(raw):
    result = collect_record(record(raw))
    assert result.salary is None
    assert result.type is result.seniority is result.modality is None
    assert result.candidates


def test_distinct_money_roles_and_multiple_candidates():
    result = collect_record(
        record(
            "Salary USD 4500.25/month\nBonus USD 1000/year\n"
            "Budget USD 750/year\nCost USD 0.004/request"
        )
    )
    assert result.salary.amounts == (Decimal("4500.25"),)
    assert [c.context.role for c in result.candidates] == [
        "base_salary",
        "bonus",
        "budget",
        "technical_cost",
    ]
    assert result.candidates[-1].amounts == (Decimal("0.004"),)
    assert len(collect_record(record("Salary USD 4500/month or USD 60000/year")).candidates) == 2
    with pytest.raises(TypeError):
        evidence_bytes(0.004)


def test_heading_negation_membership_and_derived_alignment():
    result = normalized("Requirements:\n• Python\n• No Java\nOther:\nSQL")
    candidates = collect(result)
    assert [c.context.role for c in candidates] == ["required", "negated", "mentioned"]
    first = candidates[0]
    assert first.context.list_item_ids
    assert (
        result.text[first.context.heading_span.start : first.context.heading_span.end]
        == "Requirements:"
    )
    assert candidates[1].context.cues == ("No",)
    derived = DerivedView.casefold("𐐀 ß İ SQL")
    start = derived.text.index("sql")
    assert derived.canonical_span(Span(start, start + 3)) == Span(6, 9)
    assert derived.canonical_span(Span(2, 4)) == Span(2, 3)


def test_repeated_tokens_unicode_and_conservative_origins():
    result = normalized("𐐀 a\u200b\u0301 Python Python 🇨🇷 🇨🇷 [flag:CR]")
    candidates = collect(result)
    assert [c.kind for c in candidates] == ["technology", "technology", "region", "region"]
    assert len({c.id for c in candidates}) == 4
    assert not span_errors(result)
    for candidate in candidates:
        assert result.text[candidate.span.start : candidate.span.end] == candidate.text
    flags = [c for c in candidates if c.kind == "region"]
    assert all(result.source.raw[c.origin.span.start : c.origin.span.end] == "🇨🇷" for c in flags)
    html = collect(normalized("<p>Python Python</p>", SourceFormat.HTML_FRAGMENT))
    assert all(c.origin.precision is OriginPrecision.FIELD for c in html)
    plain = collect(normalized("Python Python"))
    assert [c.origin.span for c in plain] == [Span(0, 6), Span(7, 13)]


def test_record_states_survive_extraction_and_normalization_failures():
    inputs = tuple(
        InputField(f, ExtractionStatus.PRESENT, FieldInput(f, "x" * 8193))
        if f is JobField.JOB_TITLE
        else InputField(
            f, ExtractionStatus.EXTRACTION_ERROR, error=ExtractionError("FETCH", "failed")
        )
        if f is D
        else InputField(f, ExtractionStatus.MISSING)
        for f in JobField
    )
    result = collect_record(N.normalize_record(JobInputRecord(inputs)))
    assert len(result.states) == 6
    assert result.states[:2] == (
        ("job_title", "present", "INPUT_LIMIT_EXCEEDED"),
        ("job_description", "extraction_error", "FETCH"),
    )
    assert result.candidates == () and result.salary is None


@pytest.mark.parametrize(
    "raw",
    [
        "<ul><li></li><li></li></ul>",
        "<ul><li>🇨🇷</li><li></li></ul>",
        '<div><ol start="4"><li>Interview</li><li value="9">Offer</li></ol></div>',
        "<ul><li><ul><li>𐐀 á 🇨🇷</li></ul></li></ul>",
    ],
)
def test_dom_parent_encloses_final_markers(raw):
    result = normalized(raw, SourceFormat.HTML_FRAGMENT)
    assert not span_errors(result)
    assert N.canonicalize(result) is result


def test_ablation_distinguishes_evidence_from_authorized_loss():
    from evaluation.ablations import without_rule
    from normietext.adapters import convert_source
    from normietext.stages.encoding import repair_document
    from normietext.stages.lexing import lex_document

    lexed = lex_document(repair_document(convert_source(FieldInput(D, "C++🚀Python 🇨🇷"))))
    view = without_rule(lexed, "emoji.region_token", N.policy)
    assert view.experiment == "without:emoji.region_token"
    assert not any(c.kind == "region" for c in collect(view))
    assert [c.value for c in collect(view) if c.kind == "technology"] == ["c++", "python"]
    view = without_rule(lexed, "emoji.remove", N.policy)
    assert "🚀" in view.text
    assert any(c.kind == "region" for c in collect(view))
    from normietext.errors import NormalizationError

    with pytest.raises(NormalizationError) as error:
        N.canonicalize(view)
    assert error.value.code.value == "INVALID_TYPE"
