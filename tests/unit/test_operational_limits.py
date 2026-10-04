"""Exact resource edges; no fragile wall-clock assertions."""

import pytest

from normietext import (
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
from normietext.adapters import convert_source
from normietext.errors import NormalizationError
from normietext.models import SourceEvidence, Span
from normietext.operations import measure_record
from normietext.provenance import Replacement, TrackedText
from normietext.validation import validate_input, validate_record


@pytest.mark.parametrize("field", list(JobField))
@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_each_input_limit_before_expensive_work(field, delta, monkeypatch):
    limits = ResourceLimits()
    source = FieldInput(field, "x" * (limits.for_field(field) + delta))
    if delta > 0:
        from normietext.adapters import plain_text

        monkeypatch.setattr(
            plain_text, "literal_document", lambda *a, **kw: pytest.fail("late rejection")
        )
        with pytest.raises(NormalizationError) as exc:
            JobTextNormalizer().normalize_field(source)
        assert exc.value.code == "INPUT_LIMIT_EXCEEDED"
    else:
        assert validate_input(source) is source
        assert convert_source(source).text == source.value


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_aggregate_limit_with_reachable_validated_configuration(delta):
    limits = ResourceLimits(job_description=327681)
    source = FieldInput(JobField.JOB_DESCRIPTION, "x" * (limits.record + delta))
    record = JobInputRecord(
        tuple(
            InputField(f, ExtractionStatus.PRESENT, source)
            if f is source.field
            else InputField(f, ExtractionStatus.MISSING)
            for f in JobField
        )
    )
    if delta > 0:
        with pytest.raises(NormalizationError) as exc:
            JobTextNormalizer(NormalizationPolicy(limits=limits)).normalize_record(record)
        assert exc.value.code == "INPUT_LIMIT_EXCEEDED"
    else:
        assert validate_record(record, limits) is record
    assert sum(ResourceLimits().for_field(f) for f in JobField) == 319488


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_html_nodes_exact_default_boundary(delta):
    # lxml adds html/body; each br is one descendant and one start event.
    source = FieldInput(
        JobField.JOB_DESCRIPTION, "<br>" * (19998 + delta), SourceFormat.HTML_FRAGMENT
    )
    if delta > 0:
        with pytest.raises(NormalizationError) as exc:
            convert_source(source)
        assert exc.value.code == "RESOURCE_LIMIT_EXCEEDED"
    else:
        assert convert_source(source).source.raw == source.value


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_html_depth_exact_default_boundary(delta):
    depth = 128 + delta
    source = FieldInput(
        JobField.JOB_DESCRIPTION,
        "<div>" * depth + "X" + "</div>" * depth,
        SourceFormat.HTML_FRAGMENT,
    )
    if delta > 0:
        with pytest.raises(NormalizationError) as exc:
            convert_source(source)
        assert exc.value.code == "RESOURCE_LIMIT_EXCEEDED"
    else:
        assert JobTextNormalizer().normalize_field(source).text == "X"


@pytest.mark.parametrize("raw_length", [1, 33])
@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_output_floor_and_factor_boundaries(raw_length, delta):
    raw = "x" * raw_length
    tracked = TrackedText.from_source(
        SourceEvidence.from_input(FieldInput(JobField.JOB_DESCRIPTION, raw))
    )
    length = ResourceLimits().output_limit(raw_length) + delta
    change = (Replacement(Span(0, raw_length), "y" * length, "test.expansion"),)
    if delta > 0:
        with pytest.raises(NormalizationError) as exc:
            tracked.replace(change)
        assert exc.value.code == "OUTPUT_LIMIT_EXCEEDED"
        assert tracked.text == raw
    else:
        assert len(tracked.replace(change).text) == length


@pytest.mark.parametrize("stage", ["lex", "render"])
@pytest.mark.parametrize("budget_ms", [49, 50, 51])
def test_regex_timeout_is_typed_and_never_publishes_partial(stage, budget_ms, monkeypatch):
    from normietext import rendering
    from normietext.stages import lexing

    class TimeoutPattern:
        def finditer(self, text, *, timeout):
            assert timeout == budget_ms / 1000
            raise TimeoutError("sensitive text must not escape")

    monkeypatch.setattr(
        lexing if stage == "lex" else rendering,
        "_EMAIL" if stage == "lex" else "_BREAKS",
        TimeoutPattern(),
    )
    source = FieldInput(JobField.JOB_TITLE, "ABC")
    record = JobInputRecord(
        tuple(
            InputField(f, ExtractionStatus.PRESENT, source)
            if f is source.field
            else InputField(f, ExtractionStatus.MISSING)
            for f in JobField
        )
    )
    normalizer = JobTextNormalizer(
        NormalizationPolicy(limits=ResourceLimits(regex_timeout_ms=budget_ms))
    )
    measured = measure_record(normalizer, record)
    assert measured.result.fields[0].result is None
    assert measured.result.fields[0].failure.code == "REGEX_TIMEOUT"
    assert measured.metrics["fields"][0]["timeout"]
    with pytest.raises(NormalizationError) as exc:
        normalizer.normalize_record(record, strict=True)
    assert exc.value.code == "REGEX_TIMEOUT"


def test_no_network_scripts_code_or_external_entities(tmp_path, monkeypatch):
    import socket
    import subprocess
    import urllib.request

    secret = tmp_path / "private.txt"
    secret.write_text("DO-NOT-READ-SECRET")
    executed = tmp_path / "executed.txt"

    def forbidden(*args, **kwargs):
        pytest.fail("normalization attempted external IO")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    raw = (
        f'<!DOCTYPE html [<!ENTITY ext SYSTEM "{secret.as_uri()}">]>'
        '<p>&ext;</p><script>fetch("https://example.invalid")</script>'
        '<img src="https://example.invalid/x" alt="image">'
        '<a href="https://example.invalid">visible</a>'
        f'<pre>open({str(executed)!r},"w").write("executed")</pre>'
    )
    result = JobTextNormalizer().normalize_field(
        FieldInput(JobField.JOB_DESCRIPTION, raw, SourceFormat.HTML_FRAGMENT)
    )
    assert "DO-NOT-READ-SECRET" not in result.text
    assert "fetch" not in result.text
    assert "visible" in result.text and "image" in result.text
    assert not executed.exists() and result.source.raw == raw
