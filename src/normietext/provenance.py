"""Piecewise alignment to the initial source, composed without retaining stage snapshots."""

from bisect import bisect_right
from dataclasses import dataclass, field
from hashlib import sha256
from itertools import pairwise

from normietext._validation import Validated, require
from normietext.errors import ErrorCode, ResourceLimitError
from normietext.models import Edit, Origin, OriginPrecision, SourceEvidence, Span
from normietext.policy import ResourceLimits
from normietext.serialization import canonical_hash

_DEFAULT_LIMITS = ResourceLimits()


@dataclass(frozen=True, slots=True)
class AlignmentSegment(Validated):
    output: Span
    origin: Origin
    linear: bool = False

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        require(self.output.start < self.output.end, "Empty alignment segment")
        if self.linear:
            require(self.origin.precision is OriginPrecision.EXACT, "Linear mapping must be exact")
            assert self.origin.span is not None
            require(
                self.output.end - self.output.start
                == self.origin.span.end - self.origin.span.start,
                "Linear lengths differ",
            )


def _merge(origins: list[Origin]) -> Origin:
    require(bool(origins), "No origins to merge")
    block = origins[0].source_block_id
    if any(item.source_block_id != block for item in origins):
        block = None
    if any(item.span is None for item in origins):
        return Origin(OriginPrecision.FIELD, source_block_id=block)
    spans = [item.span for item in origins if item.span is not None]
    exact = all(item.precision is OriginPrecision.EXACT for item in origins)
    exact &= all(left.end == right.start for left, right in pairwise(spans))
    return Origin(
        OriginPrecision.EXACT if exact else OriginPrecision.SEGMENT,
        Span(min(item.start for item in spans), max(item.end for item in spans)),
        block,
    )


@dataclass(frozen=True, slots=True)
class Alignment(Validated):
    source_length: int
    output_length: int
    segments: tuple[AlignmentSegment, ...]
    _starts: tuple[int, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_starts", tuple(item.output.start for item in self.segments))
        Validated.__post_init__(self)
        require(self.source_length >= 0 and self.output_length >= 0, "Negative alignment length")
        cursor = 0
        for item in self.segments:
            require(item.output.start == cursor, "Alignment must tile the output")
            require(
                item.origin.span is None or item.origin.span.end <= self.source_length,
                "Alignment origin outside initial source",
            )
            cursor = item.output.end
        require(cursor == self.output_length, "Incomplete alignment")

    @classmethod
    def identity(cls, length: int) -> Alignment:
        segments = (
            ()
            if length == 0
            else (
                AlignmentSegment(
                    Span(0, length), Origin(OriginPrecision.EXACT, Span(0, length)), True
                ),
            )
        )
        return cls(length, length, segments)

    def slice(self, span: Span) -> tuple[AlignmentSegment, ...]:
        """Clip output pieces; non-linear partial slices explicitly lose exact precision."""
        require(span.end <= self.output_length, "Span outside alignment")
        if span.start == span.end:
            return ()
        result = []
        start = max(0, bisect_right(self._starts, span.start) - 1)
        for segment_index in range(start, len(self.segments)):
            item = self.segments[segment_index]
            if item.output.start >= span.end:
                break
            left, right = max(span.start, item.output.start), min(span.end, item.output.end)
            if left >= right:
                continue
            origin = item.origin
            if item.linear:
                assert origin.span is not None
                delta = origin.span.start - item.output.start
                origin = Origin(
                    OriginPrecision.EXACT, Span(left + delta, right + delta), origin.source_block_id
                )
            elif Span(left, right) != item.output and origin.span is not None:
                origin = Origin(OriginPrecision.SEGMENT, origin.span, origin.source_block_id)
            result.append(AlignmentSegment(Span(left, right), origin, item.linear))
        return tuple(result)

    def origin_for(self, span: Span) -> Origin:
        require(span.end <= self.output_length, "Span outside alignment")
        if span.start != span.end:
            return _merge([item.origin for item in self.slice(span)])
        # At a deletion boundary both sides matter: never choose one arbitrarily.
        if not self.segments:
            return Origin(
                OriginPrecision.EXACT if self.source_length == 0 else OriginPrecision.SEGMENT,
                Span(0, self.source_length),
            )
        neighbors = []
        index = max(0, bisect_right(self._starts, span.start) - 1)
        for item in self.segments[max(0, index - 1) : index + 2]:
            if not item.output.start <= span.start <= item.output.end:
                continue
            if item.linear:
                assert item.origin.span is not None
                offset = item.origin.span.start + span.start - item.output.start
                neighbors.append(
                    Origin(OriginPrecision.EXACT, Span(offset, offset), item.origin.source_block_id)
                )
            else:
                origin = item.origin
                neighbors.append(
                    Origin(OriginPrecision.SEGMENT, origin.span, origin.source_block_id)
                    if origin.span
                    else origin
                )
        return _merge(neighbors)

    def project(self, source_span: Span) -> Span:
        """Conservative final envelope for a source range, including empty/deleted blocks.

        A many-to-many overlap selects its whole output segment. This method does
        not assert exact provenance; consult origin_for on the resulting span.
        """
        require(source_span.end <= self.source_length, "Projection outside source")
        hits: list[Span] = []
        before = 0
        for item in self.segments:
            origin = item.origin.span
            if origin is None:
                hits.append(item.output)
                continue
            if origin.end <= source_span.start:
                before = max(before, item.output.end)
            if source_span.start == source_span.end:
                intersects = origin.start <= source_span.start <= origin.end
            else:
                intersects = origin.start < source_span.end and source_span.start < origin.end
            if not intersects:
                continue
            if item.linear:
                delta = item.output.start - origin.start
                hits.append(
                    Span(
                        max(origin.start, source_span.start) + delta,
                        min(origin.end, source_span.end) + delta,
                    )
                )
            else:
                hits.append(item.output)
        if source_span.start == source_span.end and hits:
            # Empty source blocks stay empty even inside a many-to-many mapping.
            # Ambiguous anchors choose the left edge; no positional exactness claim.
            anchor = min(item.start for item in hits)
            return Span(anchor, anchor)
        return (
            Span(min(item.start for item in hits), max(item.end for item in hits))
            if hits
            else Span(before, before)
        )


def source_identity(source: SourceEvidence) -> str:
    digest = source.source_sha256
    if source.raw is not None:
        digest = sha256(source.raw.encode("utf-8")).hexdigest()
    require(digest is not None, "Stable identity requires the original content digest")
    return canonical_hash(
        {
            "domain": "normietext.source.v1",
            "field": source.field,
            "format": source.source_format,
            "sha256": digest,
            "source_ref": source.source_ref,
            "adapter": source.source_adapter_version,
        }
    )


def stable_id(
    namespace: str,
    source: SourceEvidence,
    rule_id: str,
    origin: Origin,
    *,
    occurrence: int = 0,
    discriminator: object = None,
) -> str:
    require(bool(namespace) and bool(rule_id), "ID namespace/rule required")
    require(type(occurrence) is int and occurrence >= 0, "Invalid occurrence")
    require(
        origin.span is None or origin.span.end <= source.source_length, "ID origin outside source"
    )
    return canonical_hash(
        {
            "domain": "normietext.id.v1",
            "namespace": namespace,
            "source": source_identity(source),
            "rule": rule_id,
            "origin": origin,
            "occurrence": occurrence,
            "discriminator": discriminator,
        }
    )


@dataclass(frozen=True, slots=True)
class Replacement(Validated):
    span: Span
    text: str
    rule_id: str
    exact_source: bool = False

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        require(bool(self.rule_id), "Replacement rule required")


@dataclass(frozen=True, slots=True)
class TrackedText(Validated):
    source: SourceEvidence
    text: str
    alignment: Alignment
    edits: tuple[Edit, ...] = ()

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        require(len(self.text) == self.alignment.output_length, "Text/alignment mismatch")
        require(
            self.source.source_length == self.alignment.source_length, "Source/alignment mismatch"
        )
        require(len({item.id for item in self.edits}) == len(self.edits), "Duplicate tracked edits")
        require(
            all(
                item.origin.span is None or item.origin.span.end <= self.source.source_length
                for item in self.edits
            ),
            "Edit outside source",
        )

    @classmethod
    def from_source(cls, source: SourceEvidence) -> TrackedText:
        require(source.raw is not None, "Resolve references before constructing tracked text")
        assert source.raw is not None
        return cls(source, source.raw, Alignment.identity(len(source.raw)))

    def replace(
        self,
        changes: tuple[Replacement, ...],
        *,
        limits: ResourceLimits = _DEFAULT_LIMITS,
    ) -> TrackedText:
        """Apply ordered disjoint edits once, composing every piece back to the initial source.

        exact_source is an explicit assertion by a rule with a proven whole-span
        mapping (e.g. one emoji -> token). It never implies per-character alignment.
        """
        require(type(changes) is tuple, "Changes must be an immutable tuple")
        cursor = 0
        size = len(self.text)
        previous: Span | None = None
        for change in changes:
            require(
                change.span.start >= cursor and change.span.end <= len(self.text),
                "Overlapping, unordered or out-of-bounds edits",
            )
            require(previous != change.span, "Duplicate edit position")
            cursor = change.span.end
            previous = change.span
            size += len(change.text) - (change.span.end - change.span.start)
        if size > limits.output_limit(self.source.source_length):
            raise ResourceLimitError(
                ErrorCode.OUTPUT_LIMIT_EXCEEDED, "Projected output exceeds limit"
            )
        pieces: list[str] = []
        mappings: list[AlignmentSegment] = []
        edits = list(self.edits)
        cursor = offset = 0

        def copy(span: Span) -> None:
            nonlocal offset
            pieces.append(self.text[span.start : span.end])
            for item in self.alignment.slice(span):
                mappings.append(
                    AlignmentSegment(
                        Span(
                            offset + item.output.start - span.start,
                            offset + item.output.end - span.start,
                        ),
                        item.origin,
                        item.linear,
                    )
                )
            offset += span.end - span.start

        for change in changes:
            copy(Span(cursor, change.span.start))
            if self.text[change.span.start : change.span.end] == change.text:
                copy(change.span)
            else:
                origin = self.alignment.origin_for(change.span)
                if not change.exact_source and origin.span is not None:
                    origin = Origin(OriginPrecision.SEGMENT, origin.span, origin.source_block_id)
                edits.append(
                    Edit(
                        stable_id(
                            "edit",
                            self.source,
                            change.rule_id,
                            origin,
                            occurrence=len(edits),
                            discriminator={"span": change.span, "text": change.text},
                        ),
                        change.rule_id,
                        origin,
                        change.text,
                    )
                )
                pieces.append(change.text)
                if change.text:
                    mappings.append(
                        AlignmentSegment(Span(offset, offset + len(change.text)), origin)
                    )
                offset += len(change.text)
            cursor = change.span.end
        copy(Span(cursor, len(self.text)))
        return TrackedText(
            self.source,
            "".join(pieces),
            Alignment(self.source.source_length, offset, tuple(mappings)),
            tuple(edits),
        )
