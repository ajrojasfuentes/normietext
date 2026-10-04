"""Canonical projection with independent raw provenance and local span transport."""

from dataclasses import replace

from normietext.adapters import tracked_document
from normietext.models import (
    Annotation,
    AnnotationKind,
    Block,
    BlockKind,
    FieldInput,
    FrozenMap,
    Issue,
    IssueCode,
    LexedDocument,
    LexicalToken,
    NormalizedField,
    ProtectionKind,
    SourceEvidence,
    SourceFormat,
    Span,
    TokenKind,
)
from normietext.policy import NormalizationPolicy
from normietext.provenance import Replacement, TrackedText, stable_id
from normietext.rendering import render_baseline
from normietext.stages.structure import Structure, resolve_structure
from normietext.stages.symbols import symbol_changes


class Projection:
    def __init__(self, lexed: LexedDocument, policy: NormalizationPolicy) -> None:
        self.raw = tracked_document(lexed.document)
        self.local = TrackedText.from_source(
            SourceEvidence.from_input(FieldInput(lexed.document.source.field, lexed.document.text))
        )
        self.content_map: TrackedText | None = None
        self.token_spans: dict[str, Span] = {}
        self.marker_map: TrackedText | None = None
        self.marker_spans: dict[str, Span] = {}
        self.limits = policy.limits
        # Temporary coordinates do not define an independent resource budget.
        self.local_limits = replace(
            policy.limits, output_floor=policy.limits.output_limit(self.raw.source.source_length)
        )

    def apply(self, changes: tuple[Replacement, ...]) -> None:
        self.raw = self.raw.replace(changes, limits=self.limits)
        self.local = self.local.replace(changes, limits=self.local_limits)
        if self.content_map is not None:
            self.content_map = self.content_map.replace(changes, limits=self.local_limits)
        if self.marker_map is not None:
            self.marker_map = self.marker_map.replace(changes, limits=self.local_limits)

    def span(self, span: Span, *, insertions: bool = False, trim: bool = False) -> Span:
        result = self.local.alignment.project(span)
        start, end = result.start, result.end
        if insertions:
            for segment in self.local.alignment.segments:
                origin = segment.origin.span
                if origin is not None and origin.start == origin.end == span.start:
                    start, end = min(start, segment.output.start), max(end, segment.output.end)
        if trim:
            while start < end and self.raw.text[start] in " \n":
                start += 1
            while end > start and self.raw.text[end - 1] in " \n":
                end -= 1
        return Span(start, end)

    def original_changes(self, changes: tuple[Replacement, ...]) -> None:
        self.apply(tuple(replace(c, span=self.span(c.span)) for c in changes))

    def markers(self, structure: Structure) -> None:
        merged: list[Replacement] = []
        shift = 0
        for change, owner in zip(structure.changes, structure.marker_ids, strict=True):
            change = replace(change, span=self.span(change.span))
            separator = ""
            if merged and change.span == merged[-1].span and change.span.start == change.span.end:
                separator = "\n"
                previous = merged.pop()
                merged.append(replace(previous, text=previous.text + separator + change.text))
            else:
                merged.append(change)
            start = change.span.start + shift + len(separator)
            self.marker_spans[owner] = Span(start, start + len(change.text.rstrip()))
            shift += len(separator) + len(change.text) - (change.span.end - change.span.start)
        self.apply(tuple(merged))
        self.marker_map = TrackedText.from_source(
            SourceEvidence.from_input(FieldInput(self.raw.source.field, self.raw.text))
        )

    def capture_tokens(self, tokens: tuple[LexicalToken, ...]) -> None:
        # An identity map after expansion distinguishes token content from later
        # markers inserted at the same source boundary. Raw origins stay intact.
        self.token_spans = {token.id: self.span(token.span, trim=True) for token in tokens}
        self.content_map = TrackedText.from_source(
            SourceEvidence.from_input(FieldInput(self.raw.source.field, self.raw.text))
        )

    def token_span(self, token: LexicalToken) -> Span:
        assert self.content_map is not None
        return self.content_map.alignment.project(self.token_spans[token.id])

    def block_span(self, block: Block) -> Span:
        span = self.span(block.span, trim=True)
        if block.id in self.marker_spans:
            assert self.marker_map is not None
            marker = self.marker_map.alignment.project(self.marker_spans[block.id])
            span = Span(
                marker.start,
                marker.end if block.span.start == block.span.end else max(span.end, marker.end),
            )
        return span


def _html_changes(lexed: LexedDocument, structure: Structure) -> tuple[Replacement, ...]:
    doc = lexed.document
    if doc.source.source_format is not SourceFormat.HTML_FRAGMENT:
        return ()
    changes: dict[Span, Replacement] = {}
    cells = [b for b in doc.blocks if b.kind is BlockKind.TABLE_CELL]
    items = [b for b in structure.blocks if b.kind is BlockKind.LIST_ITEM]
    paragraphs = [b for b in doc.blocks if b.kind is BlockKind.PARAGRAPH]
    # Decide paragraph spacing only at existing explicit line boundaries.
    for i, char in enumerate(doc.text):
        if char != "\n":
            continue
        value = "\n"
        if any(b.span.start <= i < b.span.end for b in cells):
            value = " "
        elif not any(b.span.start <= i < b.span.end for b in items):
            adjoining = any(b.span.end == i or b.span.start == i + 1 for b in paragraphs)
            adjacent_items = any(b.span.end == i for b in items) and any(
                b.span.start == i + 1 for b in items
            )
            if adjoining and not adjacent_items:
                value = "\n\n"
        if value != char:
            span = Span(i, i + 1)
            changes[span] = Replacement(span, value, "render.html_boundary", True)
    # Cells may be empty: the separator, not reconstructed text, defines layout.
    previous_by_row: dict[tuple[object, int | None], Block] = {}
    for cell in cells:
        key = (cell.metadata.get("table_id"), cell.row)
        previous = previous_by_row.get(key)
        if previous is not None:
            span = Span(previous.span.end, cell.span.start)
            pending = changes.get(span)
            if span.start == span.end and pending is not None:
                # Several empty cells share one source boundary. Each boundary
                # still contributes a separator; insertion identity is not span identity.
                changes[span] = replace(pending, text=pending.text + " | ")
                previous_by_row[key] = cell
                continue
            for existing in list(changes):
                if span.start <= existing.start and existing.end <= span.end:
                    del changes[existing]
            changes[span] = Replacement(span, " | ", "render.table_separator", True)
        previous_by_row[key] = cell
    by_id = {b.id: b for b in doc.blocks}
    for association in doc.associations:
        if len(association.term_ids) == len(association.definition_ids) == 1:
            term, definition = by_id[association.term_ids[0]], by_id[association.definition_ids[0]]
            span = Span(term.span.end, definition.span.start)
            if doc.text[span.start : span.end].strip():
                continue
            for existing in list(changes):
                if span.start <= existing.start and existing.end <= span.end:
                    del changes[existing]
            changes[span] = Replacement(span, ": ", "render.association", True)
    return tuple(sorted(changes.values(), key=lambda c: (c.span.start, c.span.end)))


def render_document(lexed: LexedDocument, policy: NormalizationPolicy) -> NormalizedField:
    doc = lexed.document
    structure = resolve_structure(lexed, policy)
    projection = Projection(lexed, policy)
    changes, generated = symbol_changes(lexed, structure.consumed)
    projection.apply(changes)
    projection.capture_tokens(generated)
    projection.markers(structure)
    projection.original_changes(_html_changes(lexed, structure))
    compact = doc.source.field.value in policy.output.compact_fields
    projection.raw = render_baseline(projection.raw, compact=compact, limits=policy.limits)
    projection.local = render_baseline(
        projection.local, compact=compact, limits=projection.local_limits
    )
    assert projection.marker_map is not None
    projection.marker_map = render_baseline(
        projection.marker_map, compact=compact, limits=projection.local_limits
    )
    assert projection.content_map is not None
    projection.content_map = render_baseline(
        projection.content_map, compact=compact, limits=projection.local_limits
    )
    blocks = [replace(b, span=projection.block_span(b)) for b in structure.blocks]
    # Inserted markers belong to their item and every enclosing DOM block.
    # Propagate through the tree without changing source provenance.
    by_id = {block.id: index for index, block in enumerate(blocks)}
    for block in tuple(blocks):
        parent_id = block.parent_id
        while parent_id is not None:
            index = by_id[parent_id]
            parent = blocks[index]
            blocks[index] = replace(
                parent,
                span=Span(
                    min(parent.span.start, block.span.start), max(parent.span.end, block.span.end)
                ),
            )
            parent_id = parent.parent_id
    for protection in lexed.protections:
        if protection.kind is ProtectionKind.CODE and not any(
            b.kind is BlockKind.CODE and b.span == protection.span for b in doc.blocks
        ):
            blocks.append(
                Block(
                    stable_id(
                        "block",
                        doc.source,
                        "code.lexical",
                        protection.origin,
                        discriminator=protection.span,
                    ),
                    BlockKind.CODE,
                    projection.span(protection.span, trim=True),
                    protection.origin,
                )
            )
    annotations = [
        replace(a, span=projection.span(a.span, trim=True)) if a.span is not None else a
        for a in doc.annotations
    ]
    for token in generated:
        rule = {
            TokenKind.REGION: "emoji.region_token",
            TokenKind.SUBDIVISION: "emoji.subdivision_token",
            TokenKind.HINT: "emoji.hint_token",
        }[token.kind]
        kind = {
            TokenKind.REGION: AnnotationKind.EMOJI_REGION,
            TokenKind.SUBDIVISION: AnnotationKind.EMOJI_SUBDIVISION,
            TokenKind.HINT: AnnotationKind.EMOJI_HINT,
        }[token.kind]
        annotations.append(
            Annotation(
                stable_id("annotation", doc.source, rule, token.origin, discriminator=token.span),
                kind,
                rule,
                token.origin,
                FrozenMap.from_mapping(
                    {
                        "value": token.payload["value"],
                        "source_text": doc.text[token.span.start : token.span.end],
                    }
                ),
                projection.token_span(token),
                str(token.payload["rendered_token"]),
            )
        )
    issues = [*lexed.issues, *structure.issues]
    for protection in lexed.protections:
        span = projection.span(protection.span)
        if (
            projection.raw.text[span.start : span.end]
            != doc.text[protection.span.start : protection.span.end]
        ):
            issues.append(
                Issue(
                    IssueCode.PROTECTED_SPAN_MODIFIED,
                    "render.protected_span",
                    protection.origin,
                    FrozenMap.from_mapping(
                        {"kind": protection.kind.value, "protection_id": protection.id}
                    ),
                )
            )
    assert doc.manifest is not None
    return NormalizedField(
        doc.source,
        projection.raw.text,
        doc.manifest,
        tuple(sorted(blocks, key=lambda b: (b.span.start, b.span.end, b.id))),
        doc.associations,
        tuple(sorted(annotations, key=lambda a: (a.span.start if a.span else -1, a.id))),
        projection.raw.edits,
        tuple(issues),
    )
