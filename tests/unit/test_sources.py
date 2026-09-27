from dataclasses import replace

import pytest

from normietext import (
    ErrorCode,
    ExtractionStatus,
    FieldInput,
    InputField,
    JobField,
    JobInputRecord,
    ResourceLimits,
    SourceEvidence,
    SourceFormat,
)
from normietext.errors import InputValidationError, ModelValidationError, SourceRecoveryError
from normietext.serialization import canonical_bytes
from normietext.sources import RejectedInputError, persist_source, prepare_input, recover_source
from normietext.validation import validate_input, validate_record


class Store:
    def __init__(self):
        self.values = {}

    def persist(self, source):
        self.values["record/1"] = replace(source, source_ref="record/1")
        return "record/1"

    def read(self, reference):
        return self.values[reference]


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        (None, ErrorCode.INVALID_TYPE),
        (b"private", ErrorCode.INVALID_TYPE),
        ("secret\ud800", ErrorCode.INVALID_UNICODE),
        ("x" * 9, ErrorCode.INPUT_LIMIT_EXCEEDED),
    ],
)
def test_rejection_retains_original_without_publishing_invalid_json(raw, code):
    with pytest.raises(RejectedInputError) as caught:
        prepare_input(raw, JobField.JOB_TITLE, limits=ResourceLimits(job_title=8))
    assert caught.value.code is code
    assert caught.value.rejected.value is raw
    assert "secret" not in str(caught.value)
    with pytest.raises(ModelValidationError):
        canonical_bytes(caught.value.rejected)


def test_input_gates_check_lengths_before_unicode_and_keep_exact_boundary():
    limits = ResourceLimits(job_title=2)
    assert prepare_input("ab", JobField.JOB_TITLE, limits=limits).value == "ab"
    with pytest.raises(RejectedInputError) as caught:
        prepare_input("\ud800xx", JobField.JOB_TITLE, limits=limits)
    assert caught.value.code is ErrorCode.INPUT_LIMIT_EXCEEDED
    for field, fmt, code in (
        ("invalid", SourceFormat.PLAIN_TEXT, ErrorCode.INVALID_FIELD),
        (JobField.JOB_TITLE, "html", ErrorCode.INVALID_FORMAT),
    ):
        with pytest.raises(RejectedInputError) as caught:
            prepare_input("a", field, source_format=fmt)
        assert caught.value.code is code
    with pytest.raises(InputValidationError):
        validate_input(FieldInput(JobField.JOB_TITLE, "abc"), limits)


def test_record_budget_counts_only_present_and_is_independent():
    entries = tuple(
        InputField(field, ExtractionStatus.PRESENT, FieldInput(field, "ab")) for field in JobField
    )
    record = JobInputRecord(entries)
    assert validate_record(record, ResourceLimits(record=12)) is record
    with pytest.raises(InputValidationError) as caught:
        validate_record(record, ResourceLimits(record=11))
    assert caught.value.code is ErrorCode.INPUT_LIMIT_EXCEEDED
    missing = JobInputRecord(tuple(InputField(f, ExtractionStatus.MISSING) for f in JobField))
    assert validate_record(missing, ResourceLimits(record=1)) is missing


def test_local_raw_recovers_empty_unicode_and_crlf_without_store():
    for text in ("", "San José\r\n\t💰"):
        original = FieldInput(JobField.JOB_DESCRIPTION, text)
        evidence = SourceEvidence.from_input(original)
        assert recover_source(evidence) == original
        assert evidence.source_sha256 is not None


def test_external_persistence_checks_content_metadata_and_missing_store():
    original = FieldInput(JobField.JOB_TITLE, "abc", source_adapter_version="v1")
    store = Store()
    evidence = persist_source(original, store)
    assert evidence.raw is None and evidence.source_ref == "record/1"
    assert recover_source(evidence, store).value == "abc"
    with pytest.raises(SourceRecoveryError) as caught:
        recover_source(evidence)
    assert caught.value.code is ErrorCode.SOURCE_UNAVAILABLE
    stored = store.values["record/1"]
    for corrupted in (
        replace(stored, value="xyz"),
        replace(stored, source_format=SourceFormat.UNKNOWN),
        replace(stored, field=JobField.RAW_LOCATION),
        replace(stored, source_adapter_version="v2"),
        replace(stored, source_ref="different"),
    ):
        store.values["record/1"] = corrupted
        with pytest.raises(SourceRecoveryError) as caught:
            recover_source(evidence, store)
        assert caught.value.code is ErrorCode.SOURCE_MISMATCH
    store.values.clear()
    with pytest.raises(SourceRecoveryError):
        recover_source(evidence, store)


def test_persistence_failure_never_returns_reference_only_evidence():
    class Broken(Store):
        def persist(self, source):
            return "missing"

    with pytest.raises(SourceRecoveryError):
        persist_source(FieldInput(JobField.JOB_TITLE, "private"), Broken())
