"""Apply lexical decisions with local gap repair, never broad punctuation rewriting."""

import unicodedata
from bisect import bisect_right

from normietext.models import CandidateAction, LexedDocument, LexicalToken, Span, TokenKind
from normietext.provenance import Replacement
from normietext.validation import _forbidden


def _word(char: str) -> bool:
    return bool(char) and unicodedata.category(char)[0] in "LMN"


def _technical(left: str) -> bool:
    if not left:
        return False
    if left[-1] in ")]}":
        return len(left) > 1 and (_word(left[-2]) or left[-2] in "+#%")
    if left[-1] == "%":
        return len(left) > 1 and left[-2].isnumeric()
    return left[-1] in "+#" and bool(left.rstrip("+#")) and _word(left.rstrip("+#")[-1])


def symbol_changes(
    lexed: LexedDocument, consumed: tuple[Span, ...]
) -> tuple[tuple[Replacement, ...], tuple[LexicalToken, ...]]:
    text = lexed.document.text
    cells = list(text)
    changes: dict[int, tuple[Span, str]] = {}
    generated = []
    gaps: list[Span] = []
    for token in lexed.tokens:
        span = token.span
        value = text[span.start : span.end]
        if any(c.start <= span.start and span.end <= c.end for c in consumed):
            continue
        rule = ""
        replacement = value
        if token.action is CandidateAction.TOKEN:
            replacement = str(token.payload["rendered_token"])
            rule = {
                TokenKind.REGION: "emoji.region_token",
                TokenKind.SUBDIVISION: "emoji.subdivision_token",
                TokenKind.HINT: "emoji.hint_token",
            }[token.kind]
            generated.append(token)
        elif token.kind in (TokenKind.KEYCAP, TokenKind.TEXT_SYMBOL):
            replacement = str(token.payload["base"])
            rule = "emoji.keycap_base" if token.kind is TokenKind.KEYCAP else "emoji.text_symbol"
        elif token.action is CandidateAction.REMOVE or (
            token.kind is TokenKind.LIST_MARKER and token.payload.get("fallback") == "remove"
        ):
            replacement = ""
            rule = (
                "unicode.invisible"
                if token.kind is TokenKind.INVISIBLE
                else ("kaomoji.remove" if token.kind is TokenKind.KAOMOJI else "emoji.remove")
            )
            if token.kind is not TokenKind.INVISIBLE:
                gaps.append(span)
        if replacement != value:
            changes[span.start] = (span, rule)
            cells[span.start] = replacement
            cells[span.start + 1 : span.end] = [""] * (span.end - span.start - 1)
    # Ambiguous pictographs preserve textual marks, but never retain selectors
    # or other globally forbidden format characters inside the preserved token.
    starts, ranges = _forbidden()
    for token in lexed.tokens:
        if token.kind is not TokenKind.UNCLASSIFIED:
            continue
        for index in range(token.span.start, token.span.end):
            point = ord(text[index])
            entry = bisect_right(starts, point) - 1
            if entry >= 0 and point < ranges[entry][1]:
                cells[index] = ""
                changes[index] = (Span(index, index + 1), "unicode.invisible")
    # Each deleted run is considered once against surviving neighbors. Whitespace
    # outside that run is touched only when it belongs to its punctuation gap.
    seen: set[tuple[int, int]] = set()
    for gap in gaps:
        left, right = gap.start - 1, gap.end
        while left >= 0 and not cells[left]:
            left -= 1
        while right < len(cells) and not cells[right]:
            right += 1
        if (left, right) in seen:
            continue
        seen.add((left, right))
        lchar = cells[left][-1] if left >= 0 else ""
        rchar = cells[right][0] if right < len(cells) else ""
        prefix = "".join(cells[max(0, left - 64) : left + 1])
        if _word(rchar) and (_word(lchar) or _technical(prefix)):
            cells[gap.start] = " "
        # Only whitespace within the immediate gap before a closing sign.
        a, b = left, right
        while a >= 0 and (not cells[a] or (cells[a].isspace() and "\n" not in cells[a])):
            a -= 1
        while b < len(cells) and (not cells[b] or (cells[b].isspace() and "\n" not in cells[b])):
            b += 1
        if a >= 0 and b < len(cells) and cells[b][0] in ",.;:!?)]}" and cells[a] != "\n":
            for i in range(a + 1, b):
                if cells[i] and cells[i].isspace() and "\n" not in cells[i]:
                    cells[i] = ""
                    if i not in changes:
                        changes[i] = (Span(i, i + 1), "render.removal_gap")
    # Separators are attached to the generated occurrence, never to literal tokens.
    for token in generated:
        start, end = token.span.start, token.span.end
        left, right = start - 1, end
        while left >= 0 and not cells[left]:
            left -= 1
        while right < len(cells) and not cells[right]:
            right += 1
        before = cells[left][-1] if left >= 0 else ""
        after = cells[right][0] if right < len(cells) else ""
        left_generated = any(t.span.start == left for t in generated) if before == "]" else False
        if _word(before) or (before and unicodedata.category(before) == "Sc") or left_generated:
            cells[start] = " " + cells[start]
        if _word(after) or (after and unicodedata.category(after) == "Sc"):
            cells[start] += " "
    # Fullwidth solidus is the only punctuation equivalence, outside protections.
    protected = bytearray(len(text))
    for item in lexed.protections:
        protected[item.span.start : item.span.end] = b"\1" * (item.span.end - item.span.start)
    for index, char in enumerate(text):
        if char == "\uff0f" and not protected[index]:
            cells[index] = "/"
            changes[index] = (Span(index, index + 1), "character.fullwidth_solidus")
    result = tuple(
        Replacement(span, "".join(cells[span.start : span.end]), rule, True)
        for _, (span, rule) in sorted(changes.items())
    )
    return result, tuple(generated)
