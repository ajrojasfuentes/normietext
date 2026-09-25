"""Contract and provenance failures, independent of the future normalizer."""

from dataclasses import FrozenInstanceError, replace

import pytest

from normietext.errors import ErrorCode, InputValidationError, ModelValidationError
from normietext.models import (
    Annotation,
    AnnotationKind,
    Association,
    Block,
    BlockKind,
    DocumentPhase,
    Edit,
    ExtractionError,
    ExtractionStatus,
    FieldFailure,
    FieldInput,
    FieldOutcome,
    FieldStatus,
    FrozenMap,
    InputField,
    Issue,
    IssueCode,
    JobField,
    JobInputRecord,
    Manifest,
    NormalizedField,
    NormalizedJobRecord,
    Origin,
    OriginPrecision,
    ParsedDocument,
    RecordStatus,
    SourceEvidence,
    SourceFormat,
    Span,
    freeze_json,
)


def manifest() -> Manifest:
    return Manifest(
        "1.0.0",
        "1.0.0",
        "linkedin_jobs_aggressive_v1",
        "0" * 64,
        "test-revision",
        "3.14.7",
        "16.0.0",
        "lxml",
        "2.14.6",
        (),
        (),
        (),
    )


def source(text: str = "Python") -> SourceEvidence:
    return SourceEvidence.from_input(FieldInput(JobField.JOB_DESCRIPTION, text))


def test_field_input_errors_are_typed() -> None:
    for kwargs, code in [
        ({"field": "other", "value": "x"}, ErrorCode.INVALID_FIELD),
        ({"field": JobField.JOB_TITLE, "value": None}, ErrorCode.INVALID_TYPE),
        ({"field": JobField.JOB_TITLE, "value": b"x"}, ErrorCode.INVALID_TYPE),
        ({"field": JobField.JOB_TITLE, "value": "\ud800"}, ErrorCode.INVALID_UNICODE),
        (
            {"field": JobField.JOB_TITLE, "value": "x", "source_format": "html"},
            ErrorCode.INVALID_FORMAT,
        ),
    ]:
        with pytest.raises(InputValidationError) as caught:
            FieldInput(**kwargs)
        assert caught.value.code is code
    assert FieldInput(JobField.JOB_TITLE, "").value == ""


def test_payload_is_detached_and_deeply_immutable() -> None:
    mutable = {"values": [1, {"name": "Python"}]}
    payload = FrozenMap.from_mapping(mutable)
    mutable["values"].append("changed")
    assert len(payload["values"]) == 2
    with pytest.raises(FrozenInstanceError):
        payload.entries = ()
    with pytest.raises(TypeError):
        payload["new"] = "x"
    with pytest.raises(ModelValidationError):
        FrozenMap((("bad", []),))
    for invalid in (float("nan"), float("inf"), {"x": object()}, {1: "not a string"}, "\ud800"):
        with pytest.raises(ModelValidationError):
            freeze_json(invalid)
    cycle = []
    cycle.append(cycle)
    with pytest.raises(ModelValidationError):
        freeze_json(cycle)


def test_input_states_and_exact_six_key_contract() -> None:
    missing = {f.value: InputField(f, ExtractionStatus.MISSING) for f in JobField}
    record = JobInputRecord.from_mapping(dict(reversed(list(missing.items()))))
    assert tuple(item.field for item in record.fields) == tuple(JobField)
    for bad in ({}, {**missing, "unknown": next(iter(missing.values()))}):
        with pytest.raises(InputValidationError):
            JobInputRecord.from_mapping(bad)
    with pytest.raises(ModelValidationError):
        InputField(JobField.JOB_TITLE, ExtractionStatus.PRESENT)
    with pytest.raises(ModelValidationError):
        InputField(JobField.JOB_TITLE, ExtractionStatus.MISSING, FieldInput(JobField.JOB_TITLE, ""))
    error = InputField(
        JobField.JOB_TITLE,
        ExtractionStatus.EXTRACTION_ERROR,
        error=ExtractionError("upstream", "failed", "record/1/title"),
    )
    assert error.source is None


def test_source_must_be_recoverable_and_origins_honest() -> None:
    assert source("").raw == ""
    with pytest.raises(ModelValidationError):
        SourceEvidence(JobField.JOB_TITLE, SourceFormat.PLAIN_TEXT, 1)
    with pytest.raises(ModelValidationError):
        SourceEvidence(JobField.JOB_TITLE, SourceFormat.PLAIN_TEXT, 2, raw="x")
    for args in ((-1, 2), (2, 1), (True, 2)):
        with pytest.raises(ModelValidationError):
            Span(*args)
    with pytest.raises(ModelValidationError):
        Origin(OriginPrecision.EXACT)
    with pytest.raises(ModelValidationError):
        Origin(OriginPrecision.FIELD, Span(0, 1))


def test_empty_status_preserves_issues_and_phase_cannot_be_forged() -> None:
    issue = Issue(IssueCode.PROTECTED_SPAN_MODIFIED, "test.rule", Origin(OriginPrecision.FIELD))
    result = NormalizedField(source(""), "", manifest(), issues=(issue,))
    assert result.status is FieldStatus.EMPTY and result.issues == (issue,)
    assert replace(result, text="x").status is FieldStatus.OK_WITH_ISSUES
    assert replace(result, text="x", issues=()).status is FieldStatus.OK
    assert result.phase is DocumentPhase.CANONICAL
    assert ParsedDocument(source(), "Python").phase is DocumentPhase.CONVERTED
    with pytest.raises(FrozenInstanceError):
        result.text = "changed"
    with pytest.raises(TypeError):
        replace(result, phase=DocumentPhase.CONVERTED)


def test_references_spans_and_associations_are_validated() -> None:
    origin = Origin(OriginPrecision.EXACT, Span(0, 6))
    term = Block("term", BlockKind.TERM, Span(0, 2), origin)
    definition = Block("definition", BlockKind.DEFINITION, Span(2, 6), origin)
    group = Association("pair", ("term",), ("definition",), origin, "html.dl")
    ParsedDocument(source(), "Python", (term, definition), (group,))
    invalid = [
        {"blocks": (replace(term, span=Span(0, 7)),)},
        {"blocks": (term, term)},
        {"blocks": (replace(term, parent_id="absent"),)},
        {"blocks": (replace(term, parent_id="definition"), replace(definition, parent_id="term"))},
        {
            "blocks": (term, definition),
            "associations": (replace(group, term_ids=("definition",), definition_ids=()),),
        },
        {"blocks": (replace(term, origin=Origin(OriginPrecision.SEGMENT, Span(0, 7))),)},
    ]
    for kwargs in invalid:
        with pytest.raises(ModelValidationError):
            ParsedDocument(source(), "Python", **kwargs)
    with pytest.raises(ModelValidationError):
        Block("cell", BlockKind.TABLE_CELL, Span(0, 0), origin)
    with pytest.raises(ModelValidationError):
        Block("heading", BlockKind.HEADING, Span(0, 2), origin, heading_level=7)


def test_token_spans_match_generated_text() -> None:
    text = "[flag:CR]"
    annotation = Annotation(
        "a",
        AnnotationKind.EMOJI_REGION,
        "emoji.region_token",
        Origin(OriginPrecision.EXACT, Span(0, 2)),
        FrozenMap.from_mapping({"value": "CR"}),
        Span(0, len(text)),
        text,
    )
    NormalizedField(source("🇨🇷"), text, manifest(), annotations=(annotation,))
    with pytest.raises(ModelValidationError):
        NormalizedField(
            source("🇨🇷"),
            text,
            manifest(),
            annotations=(replace(annotation, span=Span(1, len(text))),),
        )
    with pytest.raises(ModelValidationError):
        Edit("", "rule", Origin(OriginPrecision.FIELD), "")


def test_partial_record_keeps_errors_and_missing_without_fake_empty_results() -> None:
    inputs = [InputField(f, ExtractionStatus.MISSING) for f in JobField]
    raw = FieldInput(JobField.JOB_TITLE, "Python")
    inputs[0] = InputField(JobField.JOB_TITLE, ExtractionStatus.PRESENT, raw)
    failure = FieldFailure(raw, ErrorCode.REGEX_TIMEOUT, "budget exceeded")
    outcomes = tuple(
        FieldOutcome(item, failure=failure if item.source else None) for item in inputs
    )
    result = NormalizedJobRecord(outcomes)
    assert result.status is RecordStatus.PARTIAL
    assert result.fields[0].failure.source.value == "Python"
    assert all(item.result is None for item in result.fields)
    with pytest.raises(ModelValidationError):
        FieldOutcome(inputs[0])
    with pytest.raises(ModelValidationError):
        FieldOutcome(inputs[1], failure=failure)
    all_missing = NormalizedJobRecord(
        tuple(FieldOutcome(InputField(f, ExtractionStatus.MISSING)) for f in JobField)
    )
    assert all_missing.status is RecordStatus.MISSING


def test_models_have_no_mutable_instance_dictionary() -> None:
    assert not hasattr(FieldInput(JobField.JOB_TITLE, "Python"), "__dict__")
    assert not hasattr(FrozenMap(), "__dict__")
    with pytest.raises(InputValidationError):
        JobInputRecord.from_mapping(None)


def test_result_cannot_claim_another_source_reference() -> None:
    raw = FieldInput(
        JobField.JOB_DESCRIPTION,
        "Python",
        source_ref="record/1",
        source_adapter_version="adapter/1",
    )
    envelope = InputField(raw.field, ExtractionStatus.PRESENT, raw)
    evidence = SourceEvidence.from_input(raw)
    for wrong in (
        replace(evidence, source_ref="record/2"),
        replace(evidence, source_adapter_version="adapter/2"),
    ):
        with pytest.raises(ModelValidationError):
            FieldOutcome(envelope, NormalizedField(wrong, "Python", manifest()))


def test_multiple_and_missing_definition_associations_remain_explicit() -> None:
    origin = Origin(OriginPrecision.FIELD)
    terms = (
        Block("en", BlockKind.TERM, Span(0, 1), origin),
        Block("es", BlockKind.TERM, Span(1, 2), origin),
    )
    definitions = (
        Block("first", BlockKind.DEFINITION, Span(2, 3), origin),
        Block("second", BlockKind.DEFINITION, Span(3, 4), origin),
    )
    association = Association("group", ("en", "es"), ("first", "second"), origin, "html.dl")
    document = ParsedDocument(source("abcd"), "abcd", terms + definitions, (association,))
    assert len(document.associations[0].term_ids) == 2
    assert len(document.associations[0].definition_ids) == 2
    ParsedDocument(
        source("ab"), "ab", terms, (Association("orphan", ("en", "es"), (), origin, "html.dl"),)
    )


def test_record_with_six_successful_empty_fields_is_not_missing() -> None:
    outcomes = []
    for field in JobField:
        raw = FieldInput(field, "")
        outcomes.append(
            FieldOutcome(
                InputField(field, ExtractionStatus.PRESENT, raw),
                NormalizedField(SourceEvidence.from_input(raw), "", manifest()),
            )
        )
    record = NormalizedJobRecord(tuple(outcomes))
    assert record.status is RecordStatus.OK
    assert all(item.result.status is FieldStatus.EMPTY for item in record.fields)
