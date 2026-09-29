"""Read-only lexical decisions over repaired text; destructive edits belong to F5."""

import heapq
import json
from bisect import bisect_left
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files

import emoji
import regex

from normietext.adapters import tracked_document
from normietext.errors import (
    ErrorCode,
    InputValidationError,
    ResourceLimitError,
)
from normietext.models import (
    BlockKind,
    CandidateAction,
    FrozenMap,
    Issue,
    IssueCode,
    LexedDocument,
    LexicalToken,
    Protection,
    ProtectionKind,
    RepairedDocument,
    Span,
    TokenKind,
)
from normietext.policy import NormalizationPolicy
from normietext.provenance import stable_id
from normietext.stages.encoding import repair_document

_FLAGS = regex.VERSION1 | regex.UNICODE
_FENCE = regex.compile(
    r"^[ \t]*(?P<delimiter>`{3,}|~{3,})(?P<tail>[^\n]*)$", _FLAGS | regex.MULTILINE
)
_INLINE = regex.compile(r"(?<!`)(`+)(?!`)[^\n]*?(?<!`)\1(?!`)", _FLAGS)
_URL = regex.compile(r"""(?<![\p{L}\p{N}_@])(?i:https?://|ftp://|www\.)[^\s<>"`]+""", _FLAGS)
_EMAIL = regex.compile(
    r"(?<![\p{L}\p{N}_.+\-])"
    r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~\-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~\-]+)*"
    r"@(?:[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,63}"
    r"(?![\p{L}\p{N}_\-])",
    _FLAGS,
)
_KEYCAP = regex.compile(r"[0-9#*][\ufe0e\ufe0f]?\u20e3", _FLAGS)
_REGIONAL = regex.compile(r"[\U0001f1e6-\U0001f1ff]{1,2}", _FLAGS)
_SYMBOL = regex.compile(r"[©®™][\ufe0e\ufe0f]?", _FLAGS)
_MARKER = regex.compile(r"[•▪◦‣→\u2013\u2014-]", _FLAGS)
_LF = regex.compile(r"\n", _FLAGS)
_DEFAULT_POLICY = NormalizationPolicy()


def _matches(
    pattern: regex.Pattern[str], text: str, policy: NormalizationPolicy
) -> list[regex.Match[str]]:
    try:
        return list(pattern.finditer(text, timeout=policy.limits.regex_timeout_ms / 1000))
    except TimeoutError as exc:
        raise ResourceLimitError(
            ErrorCode.REGEX_TIMEOUT, "Lexical matching exceeded budget"
        ) from exc


def _class(ranges: list[list[int]]) -> str:
    return (
        "["
        + "".join(
            regex.escape(chr(start))
            if end == start + 1
            else regex.escape(chr(start)) + "-" + regex.escape(chr(end - 1))
            for start, end in ranges
        )
        + "]"
    )


@lru_cache(maxsize=1)
def _tables() -> tuple[
    dict[str, str], dict[str, tuple[str, str, str]], tuple[regex.Pattern[str], ...]
]:
    root = files("normietext").joinpath("data")

    hints = {
        item["sequence"]: item["id"]
        for item in json.loads(root.joinpath("emoji_hints.json").read_bytes())["entries"]
    }
    regions = {
        item["sequence"]: (item["kind"], item["code"], item["token"])
        for item in json.loads(root.joinpath("region_sequences.json").read_bytes())["entries"]
    }
    properties = json.loads(root.joinpath("unicode_properties.json").read_bytes())["entries"]
    pictograph = "[" + _class(properties["Extended_Pictographic"]) + "--[©®™]]"
    modifier = _class(properties["Emoji_Modifier"])
    unit = pictograph + "(?:[\ufe0e\ufe0f]|" + modifier + ")*"
    candidate = regex.compile(unit + "(?:\u200d" + unit + ")*|" + modifier + "+", _FLAGS)
    # Unknown non-presentation combining marks are retained with their pictograph;
    # never delete an arbitrary grapheme or discard an accent with an emoji.
    uncertain = regex.compile(unit + r"[\p{M}--[\ufe0e\ufe0f]]+", _FLAGS)
    invisible = regex.compile(
        "["
        + "".join(_class(properties[name]) for name in ("Cf", "Cc", "Default_Ignorable_Code_Point"))
        + "\u2800--[\t\n]]",
        _FLAGS,
    )
    kaomoji = regex.compile(
        r"(?<![\p{L}\p{M}\p{N}_])(?:"
        + "|".join(
            regex.escape(item)
            for item in json.loads(root.joinpath("kaomoji.json").read_bytes())["entries"]
        )
        + r")(?![\p{L}\p{M}\p{N}_])",
        _FLAGS,
    )
    return hints, regions, (candidate, uncertain, invisible, kaomoji)


@dataclass(frozen=True)
class _Candidate:
    start: int
    end: int
    kind: TokenKind
    action: CandidateAction
    priority: int


def _select(candidates: list[_Candidate]) -> list[_Candidate]:
    """Explicit priority, longest match, position, kind; independent of discovery order."""
    selected: list[_Candidate] = []
    starts: list[int] = []
    for item in sorted(
        candidates, key=lambda c: (c.priority, -(c.end - c.start), c.start, c.kind.value)
    ):
        index = bisect_left(starts, item.start)
        if index and selected[index - 1].end > item.start:
            continue
        if index < len(selected) and selected[index].start < item.end:
            continue
        starts.insert(index, item.start)
        selected.insert(index, item)
    return selected


def _protections(document: RepairedDocument, policy: NormalizationPolicy) -> tuple[Protection, ...]:
    text = document.text
    # Code is an overlay: it prevents list/punctuation rules, not global emoji or
    # invisible policy. Merge nested DOM code ranges without duplicating text.
    code = sorted(
        (block.span.start, block.span.end)
        for block in document.blocks
        if block.kind is BlockKind.CODE and block.span.start < block.span.end
    )
    ranges: list[tuple[int, int, ProtectionKind, str]] = []
    for start, end in code:
        if ranges and start < ranges[-1][1]:
            left, right, kind, rule = ranges[-1]
            ranges[-1] = left, max(right, end), kind, rule
        else:
            ranges.append((start, end, ProtectionKind.CODE, "lex.code_dom"))
    opened: tuple[int, str] | None = None
    for match in _matches(_FENCE, text, policy):
        delimiter = match["delimiter"]
        if opened is None:
            if not any(start <= match.start() < end for start, end, _, _ in ranges):
                opened = match.start(), delimiter
        elif (
            delimiter[0] == opened[1][0]
            and len(delimiter) >= len(opened[1])
            and not match["tail"].strip()
        ):
            ranges.append((opened[0], match.end(), ProtectionKind.CODE, "lex.code_fence"))
            opened = None
    if opened is not None:
        ranges.append((opened[0], len(text), ProtectionKind.CODE, "lex.code_fence"))
    # DOM > fence > inline > URL > email. Contacts inside code remain code.
    for pattern, kind, rule in (
        (_INLINE, ProtectionKind.CODE, "lex.code_inline"),
        (_URL, ProtectionKind.URL, "lex.url"),
        (_EMAIL, ProtectionKind.EMAIL, "lex.email"),
    ):
        for match in _matches(pattern, text, policy):
            start, end = match.span()
            if kind is ProtectionKind.URL:
                while end > start:
                    last = text[end - 1]
                    if last in ".,;:!?\"'\u2019\u201d" or (
                        last in ")] }".replace(" ", "")
                        and text[start:end].count(last)
                        > text[start:end].count({")": "(", "]": "[", "}": "{"}[last])
                    ):
                        end -= 1
                    else:
                        break
                if text[start:end].endswith(("://", "www.")):
                    continue
            if not any(left < end and start < right for left, right, _, _ in ranges):
                ranges.append((start, end, kind, rule))
    tracked = tracked_document(document)
    result = []
    for start, end, kind, rule in sorted(ranges):
        span = Span(start, end)
        origin = tracked.alignment.origin_for(span)
        result.append(
            Protection(
                stable_id("protection", document.source, rule, origin, discriminator=span),
                kind,
                span,
                origin,
                rule,
            )
        )
    return tuple(result)


class _Contexts:
    def __init__(self, entries: list[tuple[Span, str]]) -> None:
        self.entries = sorted(
            (span.start, span.end, rank, name) for rank, (span, name) in enumerate(entries)
        )
        self.index = 0
        self.active: dict[int, str] = {}
        self.ends: list[tuple[int, int]] = []

    def overlapping(self, start: int, end: int) -> tuple[str, ...]:
        while self.index < len(self.entries) and self.entries[self.index][0] < end:
            _, right, rank, name = self.entries[self.index]
            self.active[rank] = name
            heapq.heappush(self.ends, (right, rank))
            self.index += 1
        while self.ends and self.ends[0][0] <= start:
            _, rank = heapq.heappop(self.ends)
            self.active.pop(rank, None)
        return tuple(self.active[rank] for rank in sorted(self.active))


def lex_document(
    document: RepairedDocument | LexedDocument, policy: NormalizationPolicy = _DEFAULT_POLICY
) -> LexedDocument:
    """Capture complete sequences, protection and edit candidates without mutating text."""
    existing = document if isinstance(document, LexedDocument) else None
    repaired = existing.document if existing is not None else document
    if not isinstance(repaired, RepairedDocument):
        raise InputValidationError(
            ErrorCode.INVALID_TYPE, "Repair converted document before lexing"
        )
    repair_document(repaired, policy)  # Validates compatible phase; never runs ftfy again.
    if existing is not None:
        existing.__post_init__()
        return existing
    hints, regions, (pictographic, uncertain, invisible, kaomoji) = _tables()
    text = repaired.text
    protections = _protections(repaired, policy)
    candidates: list[_Candidate] = []

    def add(
        pattern: regex.Pattern[str], kind: TokenKind, action: CandidateAction, priority: int
    ) -> None:
        for match in _matches(pattern, text, policy):
            candidates.append(_Candidate(match.start(), match.end(), kind, action, priority))

    add(_SYMBOL, TokenKind.TEXT_SYMBOL, CandidateAction.KEEP, 0)
    add(_REGIONAL, TokenKind.INVALID_REGION, CandidateAction.REMOVE, 1)
    add(_KEYCAP, TokenKind.KEYCAP, CandidateAction.CONTEXTUAL, 2)
    add(uncertain, TokenKind.UNCLASSIFIED, CandidateAction.KEEP, 3)
    # Catalog sequences and the safe pictographic grammar compete by maximal
    # extent before exact allowlist classification; a hint prefix cannot split a
    # longer ZWJ sequence. Regional pairs are anchored to the beginning of a run.
    for match in emoji.analyze(text, join_emoji=False):
        if isinstance(match.value, str):
            continue
        candidates.append(
            _Candidate(
                match.value.start, match.value.end, TokenKind.EMOJI, CandidateAction.REMOVE, 4
            )
        )
    add(pictographic, TokenKind.PICTOGRAPHIC, CandidateAction.REMOVE, 4)
    add(_MARKER, TokenKind.LIST_MARKER, CandidateAction.CONTEXTUAL, 5)
    add(kaomoji, TokenKind.KAOMOJI, CandidateAction.REMOVE, 6)
    add(invisible, TokenKind.INVISIBLE, CandidateAction.REMOVE, 7)
    add(_LF, TokenKind.LINE_BREAK, CandidateAction.KEEP, 8)
    selected = _select(candidates)
    tracked = tracked_document(repaired)
    block_context = _Contexts(
        [(block.span, block.id) for block in repaired.blocks if block.span.start < block.span.end]
    )
    protection_context = _Contexts([(item.span, item.id) for item in protections])
    tokens = []
    issues = list(repaired.issues)

    def emit(start: int, end: int, kind: TokenKind, action: CandidateAction) -> None:
        if start == end:
            return
        value = text[start:end]
        payload: dict[str, object] = {}
        protected = protection_context.overlapping(start, end)
        if value in regions:
            region_kind, code, token = regions[value]
            kind = TokenKind.REGION if region_kind == "region" else TokenKind.SUBDIVISION
            action = CandidateAction.TOKEN
            payload.update(value=code, rendered_token=token)
        elif value in hints:
            kind, action = TokenKind.HINT, CandidateAction.TOKEN
            payload.update(value=hints[value], rendered_token=f"[emoji:{hints[value]}]")
        elif value.rstrip("\ufe0e\ufe0f") in (
            "👉",
            "•",
            "▪",
            "◦",
            "‣",
            "→",
            "\u2013",
            "\u2014",
            "-",
        ):
            kind, action = TokenKind.LIST_MARKER, CandidateAction.CONTEXTUAL
            payload["fallback"] = "remove" if value in emoji.EMOJI_DATA else "keep"
        elif kind in (TokenKind.KEYCAP, TokenKind.TEXT_SYMBOL):
            payload["base"] = value[0]
        elif kind is TokenKind.KAOMOJI and protected:
            action = CandidateAction.KEEP
        span = Span(start, end)
        origin = tracked.alignment.origin_for(span)
        rule = "lex." + kind.value
        tokens.append(
            LexicalToken(
                stable_id("token", repaired.source, rule, origin, discriminator=span),
                kind,
                span,
                origin,
                action,
                rule,
                FrozenMap.from_mapping(payload),
                protected,
                block_context.overlapping(start, end),
            )
        )
        if kind in (TokenKind.INVALID_REGION, TokenKind.UNCLASSIFIED):
            issues.append(
                Issue(
                    IssueCode.INVALID_REGION_SEQUENCE
                    if kind is TokenKind.INVALID_REGION
                    else IssueCode.UNCLASSIFIED_SYMBOL_SEQUENCE,
                    rule,
                    origin,
                )
            )

    context_spans = [block.span for block in repaired.blocks] + [item.span for item in protections]
    boundaries = sorted({point for span in context_spans for point in (span.start, span.end)})

    def gap(start: int, end: int) -> None:
        left, right = bisect_left(boundaries, start), bisect_left(boundaries, end)
        for point in boundaries[left:right]:
            emit(start, point, TokenKind.TEXT, CandidateAction.KEEP)
            start = point
        emit(start, end, TokenKind.TEXT, CandidateAction.KEEP)

    cursor = 0
    for candidate in selected:
        gap(cursor, candidate.start)
        emit(candidate.start, candidate.end, candidate.kind, candidate.action)
        cursor = candidate.end
    gap(cursor, len(text))
    return LexedDocument(repaired, tuple(tokens), protections, tuple(issues))
