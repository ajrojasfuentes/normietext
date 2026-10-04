"""Manual ingestion/evidence contracts for the 20 supplied synthetic jobs."""

import json

import pytest

from benchmarks.adversarial import load_samples
from benchmarks.batch import process
from normietext import ExtractionStatus, FieldInput, JobField, JobTextNormalizer


def test_ingestion_preserves_originals_without_inventing_seniority_or_format():
    for sample in load_samples():
        data = json.loads(sample.original_json)
        assert sample.modality == data["modality"]
        assert sample.criteria_items == tuple(data["criteria_list"])
        fields = sample.record.fields
        assert fields[4].state is ExtractionStatus.MISSING
        assert fields[2].source.value == "\n".join(data["criteria_list"])
        assert all(f.source.source_format == "plain_text" for f in fields if f.source)
        assert fields[1].source.value == data["description"]


@pytest.mark.parametrize("index", range(20))
def test_all_supplied_jobs_preserve_manual_evidence_sources_and_spans(index):
    result = process(index)
    assert result["errors"] == []
    assert result["metrics"]["status"] == "partial"  # missing seniority, not failed normalization
    assert all(f["error"] is None for f in result["metrics"]["fields"])


def test_maximum_ascii_description_is_not_rejected_by_irrelevant_emoji_patterns():
    raw = "x" * 262144
    result = JobTextNormalizer().normalize_field(FieldInput(JobField.JOB_DESCRIPTION, raw))
    assert result.text == raw and not result.annotations
    assert result.source.raw == raw


def test_ascii_fast_path_keeps_controls_and_list_processing():
    result = JobTextNormalizer().normalize_field(
        FieldInput(JobField.JOB_DESCRIPTION, "1. A\x00\n2. B")
    )
    assert result.text == "1. A\n2. B"
    assert sum(b.kind == "list_item" for b in result.blocks) == 2
    assert any(e.rule_id == "unicode.invisible" for e in result.edits)


@pytest.mark.parametrize(
    "text",
    [
        "ASCII " * 1000 + "✅\u0301 x 🇨🇷 👩\u200d💻 ©️ end",
        "x🛸\u0301 y✅✅ z🚀\u200d🚀\ntext",
        "漢字✅\u0301\u200bবাংলা🚀日本語",
        "".join(map(chr, range(128))) + "🚀",
    ],
)
def test_unicode_run_matching_preserves_whole_text_offsets(text):
    from normietext.stages.lexing import _NON_ASCII, _tables

    _, _, (pictographic, uncertain, _, _) = _tables()
    for pattern in (pictographic, uncertain):
        expected = [(m.start(), m.end()) for m in pattern.finditer(text)]
        segmented = [
            (run.start() + m.start(), run.start() + m.end())
            for run in _NON_ASCII.finditer(text)
            for m in pattern.finditer(run.group())
        ]
        assert segmented == expected


def test_multiline_nfc_retains_exact_composition_and_offsets():
    raw = "A\u0301\nZ\u0308\n\na\u200b\u0301 🇨🇷"
    result = JobTextNormalizer().normalize_field(FieldInput(JobField.JOB_DESCRIPTION, raw))
    assert result.text == "Á\nZ\u0308\n\ná [flag:CR]"
    flag = result.annotations[0]
    assert result.text[flag.span.start : flag.span.end] == "[flag:CR]"
    assert result.source.raw == raw
