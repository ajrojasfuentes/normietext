"""Resolve structure against repaired offsets before any destructive projection."""

import re
import unicodedata
from dataclasses import dataclass, replace

from normietext.adapters import tracked_document
from normietext.errors import ErrorCode, ResourceLimitError
from normietext.models import (
    Block,
    BlockKind,
    CandidateAction,
    FrozenMap,
    Issue,
    IssueCode,
    LexedDocument,
    SourceFormat,
    Span,
)
from normietext.policy import NormalizationPolicy
from normietext.provenance import Replacement, stable_id

_PREFIX = re.compile(
    r"(?P<bullet>[•▪◦‣👉→\u2013—-])[\ufe0e\ufe0f]?(?P<space>[^\S\n]+)(?=\S)"
    r"|(?P<number>[0-9]{1,64})(?P<suffix>\.\)|[.)]|[^\S\n]+-)[^\S\n]+(?=\S)"
    r"|(?P<circled>[①-⑳⓪])[^\S\n]*(?=\S)"
    r"|(?P<keycap>[0-9])[\ufe0e\ufe0f]?\u20e3[^\S\n]*(?=\S)"
)


@dataclass(frozen=True)
class Line:
    span: Span
    visible: str
    positions: tuple[int, ...]
    indent: int
    context: str | None
    dom: Block | None
    protected: bool


@dataclass(frozen=True)
class Marker:
    span: Span
    ordinal: int | None
    style: str
    guarded: bool = False


@dataclass(frozen=True)
class Structure:
    blocks: tuple[Block, ...]
    changes: tuple[Replacement, ...]
    issues: tuple[Issue, ...]
    consumed: tuple[Span, ...]
    marker_ids: tuple[str, ...]


def _marker(line: Line) -> Marker | None:
    stripped = line.visible.lstrip()
    match = _PREFIX.match(stripped)
    if match is None:
        return None
    offset = len(line.visible) - len(stripped)
    start = line.positions[offset]
    end = line.positions[offset + match.end() - 1] + 1
    number = match["number"] or match["keycap"]
    ordinal = int(number) if number is not None else None
    if match["circled"]:
        ordinal = int(unicodedata.numeric(match["circled"]))
    style = match["bullet"] or (
        "hyphen_number" if match["suffix"] and "-" in match["suffix"] else "number"
    )
    guarded = style in ("→", "\u2013", "—", "hyphen_number")
    body = stripped[match.end() :]
    if style == "hyphen_number" and (body[0].isnumeric() or body[0] in "+-\u2212\u2013—."):
        return None
    if style == "-" and (body[0].isnumeric() or body[0] in "+-\u2212\u2013—"):
        return None
    return Marker(Span(start, end), ordinal, style, guarded)


def _lines(lexed: LexedDocument) -> list[Line]:
    doc = lexed.document
    hidden = bytearray(len(doc.text))
    protected = bytearray(len(doc.text))
    for token in lexed.tokens:
        if token.action is CandidateAction.REMOVE:
            hidden[token.span.start : token.span.end] = b"\1" * (token.span.end - token.span.start)
    for protection in lexed.protections:
        protected[protection.span.start : protection.span.end] = b"\1" * (
            protection.span.end - protection.span.start
        )
    lines = []
    start = 0
    for text in doc.text.split("\n"):
        end = start + len(text)
        positions = tuple(i for i in range(start, end) if not hidden[i])
        visible = "".join(doc.text[i] for i in positions)
        whitespace = visible[: len(visible) - len(visible.lstrip())]
        indent = len(whitespace.expandtabs(4))
        first = next((i for i in positions if not doc.text[i].isspace()), start)
        containing = [b for b in doc.blocks if b.span.start <= first < b.span.end]
        doms = [b for b in containing if b.kind is BlockKind.LIST_ITEM]
        dom = min(doms, key=lambda b: b.span.end - b.span.start) if doms else None
        context = None
        if doc.source.source_format is SourceFormat.HTML_FRAGMENT:
            contexts = [
                b
                for b in containing
                if b.kind
                in (
                    BlockKind.CONTAINER,
                    BlockKind.TABLE_CELL,
                    BlockKind.CODE,
                    BlockKind.TERM,
                    BlockKind.DEFINITION,
                )
            ]
            if contexts:
                context = min(contexts, key=lambda b: b.span.end - b.span.start).id
        lines.append(
            Line(
                Span(start, end),
                visible,
                positions,
                indent,
                context,
                dom,
                bool(protected[first : first + 1] and protected[first]),
            )
        )
        start = end + 1
    return lines


def resolve_structure(lexed: LexedDocument, policy: NormalizationPolicy) -> Structure:
    doc = lexed.document
    tracked = tracked_document(doc)
    lines = _lines(lexed)
    candidates = [_marker(line) if not line.protected else None for line in lines]
    enabled = doc.source.field.value in policy.structure.plain_text_lists_in
    blocks = list(doc.blocks)
    changes: list[Replacement] = []
    marker_ids: list[str] = []
    consumed: list[Span] = []
    issues: list[Issue] = []
    stack: list[tuple[int, Block]] = []
    handled_dom: set[str] = set()

    def compatible(i: int, j: int) -> bool:
        return (
            0 <= j < len(lines)
            and lines[i].context == lines[j].context
            and lines[i].indent == lines[j].indent
            and not lines[j].protected
            and lines[j].dom is None
            and candidates[j] is not None
        )

    for index, (line, marker) in enumerate(zip(lines, candidates, strict=True)):
        if line.dom is not None:
            stack.clear()
            dom = line.dom
            if dom.id in handled_dom:
                continue
            handled_dom.add(dom.id)
            marker_ids.append(dom.id)
            prefix = f"{dom.ordinal}. " if dom.ordinal is not None else "- "
            if marker and marker.ordinal == dom.ordinal:
                changes.append(Replacement(marker.span, prefix, "list.redundant_marker", True))
                consumed.append(marker.span)
            else:
                point = next(
                    (i for i in line.positions if not doc.text[i].isspace()), dom.span.start
                )
                changes.append(Replacement(Span(point, point), prefix, "list.dom_marker", True))
                if marker and marker.ordinal is not None and dom.ordinal is not None:
                    issues.append(
                        Issue(
                            IssueCode.LIST_ORDINAL_CONFLICT,
                            "list.ordinal_conflict",
                            dom.origin,
                            FrozenMap.from_mapping(
                                {"dom_ordinal": dom.ordinal, "text_ordinal": marker.ordinal}
                            ),
                        )
                    )
            continue
        if not enabled or line.protected or not line.visible.strip():
            stack.clear()
            continue
        accepted = marker is not None
        if marker and marker.guarded:
            accepted = False
            for neighbor in (index - 1, index + 1):
                if not compatible(index, neighbor):
                    continue
                other = candidates[neighbor]
                assert other is not None
                if marker.style == "hyphen_number":
                    accepted |= (
                        other.ordinal is not None
                        and marker.ordinal is not None
                        and other.ordinal == marker.ordinal + neighbor - index
                    )
                else:
                    accepted |= other.style == marker.style
        if stack and index and line.context != lines[index - 1].context:
            stack.clear()
        if accepted and marker:
            while stack and stack[-1][0] > line.indent:
                stack.pop()
            peer = stack.pop()[1] if stack and stack[-1][0] == line.indent else None
            if len(stack) >= policy.limits.structural_depth:
                raise ResourceLimitError(
                    ErrorCode.RESOURCE_LIMIT_EXCEEDED, "List depth exceeds budget"
                )
            parent = stack[-1][1] if stack else None
            origin = tracked.alignment.origin_for(line.span)
            block_id = stable_id("block", doc.source, "list.item", origin, discriminator=line.span)
            same_kind = peer is not None and (peer.ordinal is None) == (marker.ordinal is None)
            list_id = (
                peer.list_id
                if same_kind and peer
                else stable_id("list", doc.source, "list.group", origin, discriminator=line.span)
            )
            block = Block(
                block_id,
                BlockKind.LIST_ITEM,
                line.span,
                origin,
                parent_id=parent.id if parent else None,
                list_id=list_id,
                ordinal=marker.ordinal,
                depth=len(stack),
                metadata=FrozenMap.from_mapping({"indent": line.indent}),
            )
            # Preserve source line identity as a child, rather than dropping origin blocks.
            blocks = [
                replace(b, parent_id=block.id)
                if b.kind is BlockKind.LINE and b.span == line.span and b.parent_id is None
                else b
                for b in blocks
            ]
            blocks.append(block)
            stack.append((line.indent, block))
            prefix = f"{marker.ordinal}. " if marker.ordinal is not None else "- "
            changes.append(Replacement(marker.span, prefix, "list.marker", True))
            marker_ids.append(block.id)
            consumed.append(marker.span)
        elif stack and line.context == lines[index - 1].context and line.indent > stack[-1][0]:
            parent = stack[-1][1]
            existing = next(
                (b for b in blocks if b.kind is BlockKind.LINE and b.span == line.span), None
            )
            if existing:
                blocks[blocks.index(existing)] = replace(
                    existing,
                    parent_id=parent.id,
                    depth=parent.depth + 1,
                    metadata=FrozenMap.from_mapping({"continuation": True}),
                )
            else:
                origin = tracked.alignment.origin_for(line.span)
                blocks.append(
                    Block(
                        stable_id(
                            "block",
                            doc.source,
                            "list.continuation",
                            origin,
                            discriminator=line.span,
                        ),
                        BlockKind.LINE,
                        line.span,
                        origin,
                        parent_id=parent.id,
                        depth=parent.depth + 1,
                        metadata=FrozenMap.from_mapping({"continuation": True}),
                    )
                )
        else:
            stack.clear()
    inferred = {b.id for b in blocks if b.kind is BlockKind.LIST_ITEM and b.origin_tag is None}
    by_id = {b.id: b for b in blocks}
    for block in sorted(blocks, key=lambda b: b.depth, reverse=True):
        current = by_id[block.id]
        if current.parent_id in inferred:
            parent = by_id[current.parent_id]
            span = Span(
                min(parent.span.start, current.span.start), max(parent.span.end, current.span.end)
            )
            by_id[parent.id] = replace(parent, span=span, origin=tracked.alignment.origin_for(span))
    blocks = [by_id[b.id] for b in blocks]
    # Empty DOM list items still have a visible canonical marker.
    for block in doc.blocks:
        if block.kind is BlockKind.LIST_ITEM and block.id not in handled_dom:
            prefix = f"{block.ordinal}. " if block.ordinal is not None else "- "
            changes.append(
                Replacement(
                    Span(block.span.start, block.span.start), prefix, "list.dom_marker", True
                )
            )
            marker_ids.append(block.id)
    ranks = {block.id: rank for rank, block in enumerate(blocks)}
    ordered = sorted(
        zip(changes, marker_ids, strict=True),
        key=lambda pair: (pair[0].span.start, pair[0].span.end, ranks[pair[1]]),
    )
    return Structure(
        tuple(blocks),
        tuple(c for c, _ in ordered),
        tuple(issues),
        tuple(consumed),
        tuple(block_id for _, block_id in ordered),
    )
