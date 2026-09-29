from dataclasses import replace

import pytest

from normietext import (
    FieldInput,
    JobField,
    Origin,
    OriginPrecision,
    ResourceLimits,
    SourceEvidence,
    Span,
)
from normietext.errors import ModelValidationError, ResourceLimitError
from normietext.provenance import Alignment, AlignmentSegment, Replacement, TrackedText, stable_id
from normietext.rendering import render_baseline


def tracked(text):
    return TrackedText.from_source(
        SourceEvidence.from_input(FieldInput(JobField.JOB_DESCRIPTION, text))
    )


def test_identity_borders_empty_and_repeated_text():
    item = tracked("abc abc")
    assert item.alignment.origin_for(Span(4, 7)) == Origin(OriginPrecision.EXACT, Span(4, 7))
    for offset in (0, 3, 7):
        assert item.alignment.origin_for(Span(offset, offset)).span == Span(offset, offset)
    assert tracked("").alignment.origin_for(Span(0, 0)) == Origin(OriginPrecision.EXACT, Span(0, 0))
    with pytest.raises(ModelValidationError):
        item.alignment.origin_for(Span(0, 8))


def test_composed_deletion_nfc_and_expansion_reach_initial_source():
    item = tracked("a\u200b\u0301 💰")
    removed = item.replace((Replacement(Span(1, 2), "", "test.remove", True),))
    tokenized = removed.replace((Replacement(Span(3, 4), "[emoji:money_bag]", "test.hint", True),))
    rendered = render_baseline(tokenized, compact=False)
    assert rendered.text == "á [emoji:money_bag]"
    assert rendered.source == item.source
    assert rendered.alignment.origin_for(Span(0, 1)) == Origin(OriginPrecision.SEGMENT, Span(0, 3))
    final = rendered.alignment.project(Span(4, 5))
    assert rendered.text[final.start : final.end] == "[emoji:money_bag]"
    assert rendered.alignment.origin_for(final) == Origin(OriginPrecision.EXACT, Span(4, 5))
    assert [(edit.rule_id, edit.origin.span) for edit in rendered.edits] == [
        ("test.remove", Span(1, 2)),
        ("test.hint", Span(4, 5)),
        ("render.nfc", Span(0, 3)),
    ]
    assert rendered.alignment.origin_for(Span(2, 3)).precision is OriginPrecision.SEGMENT


def test_equal_length_repair_is_not_implicitly_exact_and_never_regains_precision():
    item = tracked("abcd").replace((Replacement(Span(1, 3), "XY", "repair"),))
    assert item.alignment.origin_for(Span(1, 3)) == Origin(OriginPrecision.SEGMENT, Span(1, 3))
    further = item.replace((Replacement(Span(1, 2), "Z", "next", True),))
    assert further.alignment.origin_for(Span(1, 2)).precision is OriginPrecision.SEGMENT
    assert item.alignment.origin_for(Span(0, 1)).precision is OriginPrecision.EXACT


def test_deletion_boundaries_empty_output_and_insertion():
    item = tracked("abc").replace((Replacement(Span(1, 2), "", "delete", True),))
    assert item.text == "ac"
    assert item.alignment.origin_for(Span(1, 1)) == Origin(OriginPrecision.SEGMENT, Span(1, 2))
    assert item.alignment.project(Span(1, 2)) == Span(1, 1)
    empty = item.replace((Replacement(Span(0, 2), "", "delete.rest", True),))
    assert empty.text == "" and empty.alignment.origin_for(Span(0, 0)).span == Span(0, 3)
    assert len(empty.edits) == 2
    inserted = tracked("ab").replace((Replacement(Span(1, 1), " ", "separator", True),))
    assert inserted.text == "a b"
    assert inserted.alignment.origin_for(Span(1, 2)).span == Span(1, 1)
    expanded = tracked("ab").replace((Replacement(Span(0, 2), "token", "expand", True),))
    assert expanded.alignment.project(Span(1, 1)) == Span(0, 0)
    assert tracked("").alignment.project(Span(0, 0)) == Span(0, 0)


def test_invalid_alignment_and_overlaps_fail_before_output():
    with pytest.raises(ModelValidationError):
        Alignment(2, 2, (AlignmentSegment(Span(1, 2), Origin(OriginPrecision.FIELD)),))
    with pytest.raises(ModelValidationError):
        AlignmentSegment(Span(0, 2), Origin(OriginPrecision.EXACT, Span(0, 1)), True)
    item = tracked("abcd")
    for changes in (
        (Replacement(Span(0, 3), "x", "a"), Replacement(Span(2, 4), "y", "b")),
        (Replacement(Span(4, 5), "x", "a"),),
    ):
        with pytest.raises(ModelValidationError):
            item.replace(changes)
    with pytest.raises(ResourceLimitError):
        item.replace(
            (Replacement(Span(0, 4), "x" * 129, "expand"),), limits=ResourceLimits(output_floor=1)
        )
    assert item.text == "abcd" and not item.edits


def test_stable_ids_distinguish_positions_rules_source_field_and_occurrence():
    source = tracked("x x").source
    origin = Origin(OriginPrecision.EXACT, Span(0, 1))
    base = stable_id("annotation", source, "rule", origin)
    assert base == stable_id("annotation", source, "rule", origin)
    alternatives = [
        stable_id("annotation", source, "rule", Origin(OriginPrecision.EXACT, Span(2, 3))),
        stable_id("edit", source, "rule", origin),
        stable_id("annotation", source, "other", origin),
        stable_id("annotation", replace(source, field=JobField.JOB_TITLE), "rule", origin),
        stable_id("annotation", source, "rule", origin, occurrence=1),
        stable_id("annotation", replace(source, source_ref="other"), "rule", origin),
    ]
    assert len({base, *alternatives}) == 7


@pytest.mark.parametrize(
    ("raw", "compact", "expected"),
    [
        (" \tA\r\n  B\n\n\n C \n", False, "A\nB\n\nC"),
        (" \tA\r\n  B\n\n\n C \n", True, "A B C"),
        ("2\u202f400\u00a0000", True, "2 400 000"),
        ("A\x85B\u2028C\u2029D\vE\fF", False, "A\nB\nC\nD\nE\nF"),
        ("a\u0301", False, "á"),
        ("\u1100\u1161\u11a8", False, "각"),
        ("💰\u200d\ufe0f", False, "💰\u200d\ufe0f"),
        ("<b>C++</b>&amp;", True, "<b>C++</b>&amp;"),
    ],
)
def test_baseline_spacing_nfc_is_not_a_partial_cleaner(raw, compact, expected):
    result = render_baseline(tracked(raw), compact=compact)
    assert result.text == expected
    assert render_baseline(result, compact=compact) == result


def test_field_precision_survives_composition_without_fabricated_offsets():
    source = tracked("<p>text</p>").source
    converted = TrackedText(
        source,
        "text",
        Alignment(
            source.source_length, 4, (AlignmentSegment(Span(0, 4), Origin(OriginPrecision.FIELD)),)
        ),
    )
    repaired = converted.replace((Replacement(Span(0, 4), "Text", "repair", True),))
    assert repaired.alignment.origin_for(Span(0, 4)).precision is OriginPrecision.FIELD
    assert repaired.edits[0].origin.span is None


def test_renderer_timeout_is_operational_and_keeps_original(monkeypatch):
    import normietext.rendering as rendering

    class Slow:
        def finditer(self, *args, **kwargs):
            raise TimeoutError

    monkeypatch.setattr(rendering, "_GRAPHEMES", Slow())
    original = tracked("private\u0301")
    with pytest.raises(ResourceLimitError) as caught:
        rendering.render_baseline(original, compact=False)
    from normietext import ErrorCode

    assert caught.value.code is ErrorCode.REGEX_TIMEOUT
    assert original.text == "private\u0301" and not original.edits


def test_fixed_identity_vector_matches_documented_wire_formula():
    import json
    from pathlib import Path

    from normietext.provenance import source_identity
    from normietext.serialization import canonical_bytes

    vector = json.loads((Path(__file__).parents[1] / "vectors/stable_id_v1.json").read_text())
    source = tracked("x x").source
    assert source_identity(source) == vector["source_identity"]
    assert canonical_bytes(vector["id_payload"]).decode("utf-8") == vector["id_bytes_utf8"]
    assert (
        stable_id("annotation", source, "test.rule", Origin(OriginPrecision.EXACT, Span(0, 1)))
        == vector["id_sha256"]
    )
