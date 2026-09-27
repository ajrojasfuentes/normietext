"""Renderer foundations only: use AFTER lexical/structural capture, never as a cleaner API."""

import unicodedata
from collections.abc import Callable

import regex

from normietext.errors import ErrorCode, ResourceLimitError
from normietext.models import Span
from normietext.policy import ResourceLimits
from normietext.provenance import Replacement, TrackedText

_DEFAULT_LIMITS = ResourceLimits()


_FLAGS = regex.VERSION1 | regex.UNICODE
_BREAKS = regex.compile(r"\r\n|[\r\x85\u2028\u2029\v\f]", _FLAGS)
_HORIZONTAL = regex.compile(r"[^\S\n]+", _FLAGS)
_SPACES = regex.compile(r" +", _FLAGS)
_EDGES = regex.compile(r"^ +| +$", _FLAGS | regex.MULTILINE)
_BLANKS = regex.compile(r"\n{3,}", _FLAGS)
_FIELD_EDGES = regex.compile(r"\A[ \n]+|[ \n]+\Z", _FLAGS)
_GRAPHEMES = regex.compile(r"\X", _FLAGS)
_LF = regex.compile(r"\n", _FLAGS)


def _sub(
    tracked: TrackedText,
    pattern: regex.Pattern[str],
    transform: Callable[[str], str],
    rule: str,
    limits: ResourceLimits,
) -> TrackedText:
    try:
        changes = tuple(
            Replacement(Span(match.start(), match.end()), replacement, rule, True)
            for match in pattern.finditer(tracked.text, timeout=limits.regex_timeout_ms / 1000)
            if (replacement := transform(match.group())) != match.group()
        )
    except TimeoutError as exc:
        raise ResourceLimitError(
            ErrorCode.REGEX_TIMEOUT, "Renderer matching exceeded budget"
        ) from exc
    return tracked.replace(changes, limits=limits)


def render_baseline(
    tracked: TrackedText,
    *,
    compact: bool,
    limits: ResourceLimits = _DEFAULT_LIMITS,
) -> TrackedText:
    """Project already recognized text. Preserves emoji/invisibles for future stages.

    This foundation deliberately returns TrackedText, never NormalizedField.
    Its tests establish spacing/NFC composition, not the full normalization policy.
    """
    tracked = _sub(tracked, _BREAKS, lambda _: "\n", "render.line_break", limits)
    # Explicit TAB and Unicode Zs only; other controls belong to later lexical rules.
    tracked = _sub(
        tracked,
        _HORIZONTAL,
        lambda text: "".join(
            " " if c == "\t" or unicodedata.category(c) == "Zs" else c for c in text
        ),
        "render.horizontal",
        limits,
    )
    if compact:
        tracked = _sub(tracked, _LF, lambda _: " ", "render.compact", limits)
    tracked = _sub(tracked, _SPACES, lambda _: " ", "render.space_run", limits)
    tracked = _sub(tracked, _EDGES, lambda _: "", "render.line_edges", limits)
    tracked = _sub(tracked, _BLANKS, lambda _: "\n\n", "render.blank_lines", limits)
    tracked = _sub(tracked, _FIELD_EDGES, lambda _: "", "render.field_edges", limits)
    tracked = _sub(
        tracked, _GRAPHEMES, lambda text: unicodedata.normalize("NFC", text), "render.nfc", limits
    )
    # Guard against differing grapheme/NFC Unicode authorities. Never infer a
    # character map by length; a cross-boundary repair degrades to whole segment.
    normalized = unicodedata.normalize("NFC", tracked.text)
    if normalized != tracked.text:
        tracked = tracked.replace(
            (Replacement(Span(0, len(tracked.text)), normalized, "render.nfc_boundary"),),
            limits=limits,
        )
    return tracked
