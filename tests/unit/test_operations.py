"""Operational reports are opt-in, content-free, and isolated across concurrent calls."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from normietext import (
    ExtractionError,
    ExtractionStatus,
    FieldInput,
    InputField,
    JobField,
    JobInputRecord,
    JobTextNormalizer,
    NormalizationPolicy,
    ResourceLimits,
    SourceFormat,
)
from normietext._telemetry import capture
from normietext.operations import measure_field, measure_record
from normietext.serialization import canonical_bytes


def test_metrics_do_not_change_canonical_bytes_or_expose_content(capsys, caplog):
    source = FieldInput(
        JobField.JOB_DESCRIPTION,
        "Private person secret@example.org 🇨🇷 ✅\u200b",
        source_adapter_version="PRIVATE-SCRAPER",
        source_ref="PRIVATE-REF",
    )
    n = JobTextNormalizer()
    expected = canonical_bytes(n.normalize_field(source))
    measured = measure_field(n, source)
    assert canonical_bytes(measured.result) == expected
    assert measured.error is None and measured.trace == ()
    exported = canonical_bytes(measured.metrics)
    for secret in (b"Private", b"secret@example.org", b"PRIVATE-SCRAPER", b"PRIVATE-REF"):
        assert secret not in exported
    assert set(measured.metrics["stage_seconds"]) == {
        "convert",
        "repair",
        "lex",
        "render",
        "validate",
    }
    assert measured.metrics["input_codepoints"] == len(source.value)
    assert measured.metrics["annotations_by_kind"]["emoji_region"] == 1
    assert measured.metrics["edits_by_rule"]["unicode.invisible"] == 1
    assert not capsys.readouterr().out and not caplog.records
    assert capture.get() is None
    traced = measure_field(n, source, trace=True)
    assert traced.trace and canonical_bytes(traced.result) == expected
    assert canonical_bytes(traced.metrics).find(b"secret@example.org") == -1


def test_failures_empty_and_partial_record_metrics():
    n = JobTextNormalizer(NormalizationPolicy(limits=ResourceLimits(job_title=2)))
    bad = FieldInput(JobField.JOB_TITLE, "secret")
    measurement = measure_field(n, bad)
    assert measurement.result is None and measurement.error == "INPUT_LIMIT_EXCEEDED"
    empty = measure_field(n, FieldInput(JobField.JOB_DESCRIPTION, "🚀"))
    assert not empty.metrics["empty_before"] and empty.metrics["empty_after"]
    fields = tuple(InputField(f, ExtractionStatus.MISSING) for f in JobField)
    record = JobInputRecord(
        (
            InputField(bad.field, ExtractionStatus.PRESENT, bad),
            InputField(
                JobField.JOB_DESCRIPTION,
                ExtractionStatus.EXTRACTION_ERROR,
                error=ExtractionError("private-code", "private-message"),
            ),
            *fields[2:],
        )
    )
    measured = measure_record(n, record)
    assert measured.metrics["partial"]
    assert len(measured.metrics["fields"]) == 6
    assert b"private" not in canonical_bytes(measured.metrics)
    assert measured.metrics["fields"][0]["error"] == "INPUT_LIMIT_EXCEEDED"


def test_concurrent_policies_order_and_measurements_are_independent():
    ordinary = JobTextNormalizer()
    limited = JobTextNormalizer(replace(ordinary.policy, limits=ResourceLimits(job_title=2)))
    sources = [
        FieldInput(JobField.JOB_TITLE, "ABC"),
        FieldInput(JobField.JOB_DESCRIPTION, "<p>🇨🇷 ABC</p>", SourceFormat.HTML_FRAGMENT),
    ]
    calls = [(n, s) for n in (ordinary, limited) for s in sources] * 3
    expected = [measure_field(n, s) for n, s in calls]
    with ThreadPoolExecutor(max_workers=4) as pool:
        actual = list(pool.map(lambda call: measure_field(*call), calls))
    assert [(x.error, canonical_bytes(x.result)) for x in actual] == [
        (x.error, canonical_bytes(x.result)) for x in expected
    ]
    assert ordinary.policy.limits.job_title == 8192
    assert all(
        x.metrics["input_codepoints"] == len(s.value)
        for x, (_, s) in zip(actual, calls, strict=True)
    )
    assert capture.get() is None
