import unicodedata

from hypothesis import given
from hypothesis import strategies as st

from normietext import FieldInput, JobField, OriginPrecision, SourceEvidence, Span
from normietext.provenance import Replacement, TrackedText
from normietext.rendering import render_baseline


@given(st.text(alphabet="ab áé\u0301\t\r\n\u00a0", max_size=80), st.booleans())
def test_spacing_nfc_projection_is_stable_and_all_origins_stay_in_source(raw, compact):
    source = SourceEvidence.from_input(FieldInput(JobField.JOB_DESCRIPTION, raw))
    result = render_baseline(TrackedText.from_source(source), compact=compact)
    assert unicodedata.is_normalized("NFC", result.text)
    assert "  " not in result.text and "\n\n\n" not in result.text
    assert all(line == line.strip(" ") for line in result.text.split("\n"))
    assert result.text == result.text.strip(" \n")
    assert result.source.raw == raw
    assert render_baseline(result, compact=compact) == result
    assert all(s.origin.span.end <= len(raw) for s in result.alignment.segments)
    if compact:
        assert "\n" not in result.text


@given(st.text(alphabet="abcdef", min_size=3, max_size=80))
def test_deletion_does_not_shift_later_origins_or_claim_exact_across_gap(raw):
    source = SourceEvidence.from_input(FieldInput(JobField.JOB_TITLE, raw))
    item = TrackedText.from_source(source).replace((Replacement(Span(1, 2), "", "remove", True),))
    assert item.text == raw[:1] + raw[2:]
    assert item.alignment.origin_for(Span(1, len(item.text))).span == Span(2, len(raw))
    assert item.alignment.origin_for(Span(0, len(item.text))).precision is OriginPrecision.SEGMENT
