"""Execute independently authored F1 goldens; never rewrite expected output."""

import json
from collections import Counter
from pathlib import Path

import pytest

from normietext import FieldInput, JobField, JobTextNormalizer, SourceFormat
from normietext.errors import NormalizationError
from normietext.serialization import canonical_bytes

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CASES = json.loads((FIXTURES / "regression/cases.json").read_bytes())["cases"]
NORMALIZER = JobTextNormalizer()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_normative_regression(case):
    raw = case["raw"]
    if case["input_type"] == "bytes_hex":
        raw = bytes.fromhex(raw)
    field = JobField(case["field"]) if case["field"] in JobField else case["field"]

    def run():
        return NORMALIZER.normalize_field(
            FieldInput(field, raw, SourceFormat(case["source_format"]))
        )

    expected = case["expected"]
    if "error" in expected:
        with pytest.raises(NormalizationError) as error:
            run()
        assert error.value.code == expected["error"]
        return
    result = run()
    if "text" in expected:
        assert result.text == expected["text"]
    assert result.source.raw == raw
    assert NORMALIZER.canonicalize(result) is result
    assert canonical_bytes(run()) == canonical_bytes(result)
    for annotation in expected["annotations"]:
        assert (
            sum(
                a.kind == annotation["kind"] and a.payload.get("value") == annotation["value"]
                for a in result.annotations
            )
            == annotation["count"]
        )
    for structure in expected["structure"]:
        blocks = [b for b in result.blocks if b.kind == structure["kind"]]
        assert len(blocks) == structure["count"]
        if "ordinals" in structure:
            assert [b.ordinal for b in blocks] == structure["ordinals"]
        if "coordinates" in structure:
            assert [[b.row, b.column] for b in blocks] == structure["coordinates"]
    if "no_generated_annotations" in expected["properties"]:
        assert not result.annotations
    if "destructive_edit_attributed" in expected["properties"]:
        assert any(e.rule_id == "unicode.invisible" for e in result.edits)
    if "encoding_edit_attributed" in expected["properties"]:
        assert any(e.rule_id == "encoding.fix_encoding" for e in result.edits)


def test_integral_text_hints_lists_and_continuations():
    root = FIXTURES / "integral/complex_multilingual_ai_role_001"
    fixture = json.loads((root / "fixture.json").read_bytes())
    for field in ("job_title", "job_description"):
        raw = (root / f"{field}.raw.txt").read_bytes().decode()
        expected = (root / f"{field}.expected.txt").read_bytes().decode()
        result = NORMALIZER.normalize_field(FieldInput(JobField(field), raw))
        assert result.text == expected
        assert NORMALIZER.canonicalize(result) is result
        if field == "job_description":
            counts = Counter((a.kind.value, a.payload["value"]) for a in result.annotations)
            assert counts == {
                (a["kind"], a["value"]): a["count"] for a in fixture["expected_annotations"]
            }
            lists = Counter(b.list_id for b in result.blocks if b.kind == "list_item")
            assert list(lists.values()) == [11, 8, 11, 7, 6, 10]
            continuations = [b for b in result.blocks if b.metadata.get("continuation")]
            assert len(continuations) >= 4
            by_id = {b.id: b for b in result.blocks}
            assert all(by_id[b.parent_id].kind == "list_item" for b in continuations)


@pytest.mark.parametrize(
    "case",
    json.loads((FIXTURES / "supplemental/cases.json").read_bytes())["cases"],
    ids=lambda c: c["id"],
)
def test_supplemental(case):
    result = NORMALIZER.normalize_field(
        FieldInput(JobField(case["field"]), case["raw"], SourceFormat(case["source_format"]))
    )
    expected = case["expectation"]
    resolved = {
        "html_ordinal_conflict": "3. 1. X",
        "technical_boundary_0": "C++ Python",
        "technical_boundary_1": "C# Java",
        "technical_boundary_2": "(Remote) LATAM",
        "technical_boundary_3": "100% bonus",
        "technical_boundary_4": "C++",
        "technical_boundary_5": "$500",
    }
    text = expected.get("text") or resolved.get(case["id"])
    if text is not None:
        assert result.text == text
    if "association_count" in expected:
        assert len(result.associations) == expected["association_count"]
    for label, kind in [("terms", "term"), ("definitions", "definition")]:
        if label in expected:
            assert [
                result.text[b.span.start : b.span.end] for b in result.blocks if b.kind == kind
            ] == expected[label]
    if "edit_rule" in expected:
        assert any(e.rule_id == expected["edit_rule"] for e in result.edits)
    if "issue" in expected:
        assert any(i.code == expected["issue"] for i in result.issues)
    if "output_length_with_separators" in expected:
        assert len(result.text) == expected["output_length_with_separators"]
        assert len(result.annotations) == 2000


@pytest.mark.parametrize(
    "case",
    json.loads((FIXTURES / "canonical/cases.json").read_bytes())["cases"],
    ids=lambda c: c["id"],
)
def test_phase5_decisions(case):
    result = NORMALIZER.normalize_field(
        FieldInput(JobField(case["field"]), case["raw"], SourceFormat(case["source_format"]))
    )
    expected = case["expected"]
    assert result.text == expected["text"]
    assert NORMALIZER.canonicalize(result) is result
    if "items" in expected:
        assert sum(b.kind == "list_item" for b in result.blocks) == expected["items"]
    if "annotations" in expected:
        assert len(result.annotations) == expected["annotations"]
    if "associations" in expected:
        assert len(result.associations) == expected["associations"]
    if "rule" in expected:
        assert any(e.rule_id == expected["rule"] for e in result.edits)
    if "issue" in expected:
        assert any(i.code == expected["issue"] for i in result.issues)


def test_six_present_record_fixture():
    from normietext import ExtractionStatus, InputField, JobInputRecord, RecordStatus

    fixture = json.loads((FIXTURES / "records/six_present.json").read_bytes())
    record = JobInputRecord(
        tuple(
            InputField(
                field,
                ExtractionStatus.PRESENT,
                FieldInput(
                    field,
                    fixture["fields"][field.value]["raw"],
                    SourceFormat(fixture["fields"][field.value]["source_format"]),
                ),
            )
            for field in JobField
        )
    )
    result = NORMALIZER.normalize_record(record)
    assert result.status is RecordStatus.OK
    assert [outcome.result.text for outcome in result.fields] == [
        "Python Engineer",
        "- Build APIs\n- Write tests",
        "Employment type: Full-time",
        "Full-time",
        "Not Specified",
        "San José, CR",
    ]
    assert all(outcome.result.source.raw == outcome.input.source.value for outcome in result.fields)
