"""Lexical safety, overlap and context; no F5 destructive transformations."""

from dataclasses import replace

import pytest

from normietext import (
    CandidateAction,
    ErrorCode,
    FieldInput,
    IssueCode,
    JobField,
    NormalizationPolicy,
    OriginPrecision,
    ProtectionKind,
    SourceFormat,
    TokenKind,
)
from normietext.adapters import convert_source
from normietext.errors import InputValidationError, PolicyMismatchError, ResourceLimitError
from normietext.serialization import canonical_bytes
from normietext.stages.encoding import repair_document
from normietext.stages.lexing import lex_document


def lex(raw, fmt=SourceFormat.PLAIN_TEXT):
    return lex_document(
        repair_document(convert_source(FieldInput(JobField.JOB_DESCRIPTION, raw, fmt)))
    )


def test_complete_sequences_and_region_pairing_do_not_consume_letters_or_shift_pairs():
    raw = "A👩🏽\u200d💻B 🇦🇦🇨🇷 🇿 ©️ C# 1️⃣ 1 \ue000"
    result = lex(raw)
    assert result.document.text == raw
    chosen = [
        (raw[t.span.start : t.span.end], t.kind)
        for t in result.tokens
        if t.kind not in (TokenKind.TEXT, TokenKind.LINE_BREAK)
    ]
    assert chosen == [
        ("👩🏽\u200d💻", TokenKind.EMOJI),
        ("🇦🇦", TokenKind.INVALID_REGION),
        ("🇨🇷", TokenKind.REGION),
        ("🇿", TokenKind.INVALID_REGION),
        ("©️", TokenKind.TEXT_SYMBOL),
        ("1️⃣", TokenKind.KEYCAP),
    ]
    assert sum(i.code is IssueCode.INVALID_REGION_SEQUENCE for i in result.issues) == 2
    assert all(t.origin.precision is OriginPrecision.EXACT for t in result.tokens)
    assert all(
        raw[t.origin.span.start : t.origin.span.end] == raw[t.span.start : t.span.end]
        for t in result.tokens
    )


def test_unknown_pictographic_grammar_retains_mixed_marks_and_ordinary_unknown_symbols():
    result = lex("\U0001fc00\u200d🚀 🚀\u0301 a\u200d🚀 \ue000")
    assert any(t.kind is TokenKind.PICTOGRAPHIC for t in result.tokens)
    mixed = next(t for t in result.tokens if t.kind is TokenKind.UNCLASSIFIED)
    assert result.document.text[mixed.span.start : mixed.span.end] == "🚀\u0301"
    assert mixed.action is CandidateAction.KEEP
    assert IssueCode.UNCLASSIFIED_SYMBOL_SEQUENCE in {i.code for i in result.issues}


def test_dom_code_contacts_and_plain_contexts_remain_distinct():
    raw = "<p>Ordinary 24\uff0f7 <code>--flag 1. x 🚀</code> tail</p><p>jobs+ai@example.com</p>"
    result = lex(raw, SourceFormat.HTML_FRAGMENT)
    code = next(p for p in result.protections if p.kind is ProtectionKind.CODE)
    assert result.document.text[code.span.start : code.span.end] == "--flag 1. x 🚀"
    emoji_token = next(t for t in result.tokens if t.kind is TokenKind.EMOJI)
    assert code.id in emoji_token.protection_ids
    assert emoji_token.action is CandidateAction.REMOVE  # F5 applies the candidate.
    assert result.document.text.endswith("jobs+ai@example.com")
    tail = next(
        t for t in result.tokens if "tail" in result.document.text[t.span.start : t.span.end]
    )
    assert not tail.protection_ids
    assert all(t.origin.precision is OriginPrecision.FIELD for t in result.tokens)
    assert emoji_token.block_ids


def test_lexical_code_delimiters_no_language_inference_and_contact_punctuation():
    raw = (
        "before\n```python\n1. x 🚀 https://example.com\n```\nafter `x\uff0fy` "
        "(HTTPS://example.com/a(b)?q=1). jobs+ai@example.com, talent [at] example dot com"
    )
    result = lex(raw)
    spans = [(result.document.text[p.span.start : p.span.end], p.kind) for p in result.protections]
    assert spans == [
        ("```python\n1. x 🚀 https://example.com\n```", ProtectionKind.CODE),
        ("`x\uff0fy`", ProtectionKind.CODE),
        ("HTTPS://example.com/a(b)?q=1", ProtectionKind.URL),
        ("jobs+ai@example.com", ProtectionKind.EMAIL),
    ]
    assert not lex("for i in range(len(xs)):\n  work(i)").protections
    assert not lex("unmatched ` code").protections
    assert len(lex("~~~\nopen code").protections) == 1


def test_hint_literals_markers_indentation_and_kaomoji_are_not_applied():
    raw = "\t🚀• Python\n  👉 SQL\n[flag:CR] ✅ ¯\\_(ツ)_/¯ (+506) :) aಠ_ಠb"
    result = lex(raw)
    assert result.document.text == raw
    assert sum(t.kind is TokenKind.HINT for t in result.tokens) == 1
    assert sum(t.kind is TokenKind.REGION for t in result.tokens) == 0
    assert sum(t.kind is TokenKind.KAOMOJI for t in result.tokens) == 1
    assert sum(t.kind is TokenKind.LIST_MARKER for t in result.tokens) == 2
    assert not result.document.annotations
    assert not result.document.edits


def test_lexical_candidates_independent_of_catalog_iteration(monkeypatch):
    from normietext.stages import lexing

    raw = "x👩🏽\u200d💻y ⚠\ufe0e 🇦🇦🇨🇷 ✅"
    baseline = lex(raw)
    original = lexing.emoji.analyze

    def reversed_catalog(*args, **kwargs):
        return iter(reversed(list(original(*args, **kwargs))))

    monkeypatch.setattr(lexing.emoji, "analyze", reversed_catalog)
    assert canonical_bytes(lex(raw)) == canonical_bytes(baseline)


def test_lexing_requires_repair_and_rejects_incompatible_manifest():
    converted = convert_source(FieldInput(JobField.JOB_TITLE, "x"))
    with pytest.raises(InputValidationError):
        lex_document(converted)
    repaired = repair_document(converted)
    policy = NormalizationPolicy()
    with pytest.raises(PolicyMismatchError):
        lex_document(repaired, replace(policy, limits=replace(policy.limits, regex_timeout_ms=51)))


def test_lexical_regex_timeout_is_typed_and_never_returns_partial_output(monkeypatch):
    from normietext.stages import lexing

    repaired = repair_document(convert_source(FieldInput(JobField.JOB_TITLE, "original")))

    class Slow:
        def finditer(self, *args, **kwargs):
            raise TimeoutError

    monkeypatch.setattr(lexing, "_URL", Slow())
    with pytest.raises(ResourceLimitError) as caught:
        lex_document(repaired)
    assert caught.value.code is ErrorCode.REGEX_TIMEOUT
    assert repaired.text == "original"


def test_marker_presentation_variants_survive_for_structural_decision():
    result = lex("▪️ Python\n👉︎ SQL")
    assert [
        (result.document.text[t.span.start : t.span.end], t.action)
        for t in result.tokens
        if t.kind is TokenKind.LIST_MARKER
    ] == [
        ("▪️", CandidateAction.CONTEXTUAL),
        ("👉︎", CandidateAction.CONTEXTUAL),
    ]


def test_token_partition_and_context_references_are_validated():
    from normietext import Span
    from normietext.errors import ModelValidationError

    result = lex("a🚀b")
    with pytest.raises(ModelValidationError):
        replace(result, tokens=result.tokens[1:])
    with pytest.raises(ModelValidationError):
        replace(
            result,
            tokens=(replace(result.tokens[0], protection_ids=("absent",)), *result.tokens[1:]),
        )
    with pytest.raises(ModelValidationError):
        replace(result, tokens=(replace(result.tokens[0], span=Span(0, 2)), *result.tokens[1:]))
