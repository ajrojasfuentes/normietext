"""Leave-one-planned-rule-out experiments, deliberately NOT canonical documents.

Recognition remains fixed. Suppression measures the contribution/interactions of
individual planned edits and their structural metadata, not an alternate profile.
"""

from dataclasses import replace

from evaluation.evidence import EvidenceView
from normietext.models import Annotation, AnnotationKind, LexedDocument
from normietext.policy import NormalizationPolicy
from normietext.rendering import render_baseline
from normietext.stages.rendering import Projection, _html_changes
from normietext.stages.structure import resolve_structure
from normietext.stages.symbols import symbol_changes

RULES = (
    "list.marker",
    "list.redundant_marker",
    "list.dom_marker",
    "emoji.remove",
    "emoji.keycap_base",
    "emoji.text_symbol",
    "emoji.hint_token",
    "emoji.region_token",
    "emoji.subdivision_token",
    "kaomoji.remove",
    "unicode.invisible",
    "character.fullwidth_solidus",
    "render.removal_gap",
)
_TOKEN_RULES = {
    "region": "emoji.region_token",
    "subdivision": "emoji.subdivision_token",
    "hint": "emoji.hint_token",
}
_TOKEN_KINDS = {
    "region": AnnotationKind.EMOJI_REGION,
    "subdivision": AnnotationKind.EMOJI_SUBDIVISION,
    "hint": AnnotationKind.EMOJI_HINT,
}


def without_rule(lexed: LexedDocument, rule: str, policy: NormalizationPolicy) -> EvidenceView:
    if rule not in RULES:
        raise ValueError("Unknown ablation rule")
    structure = resolve_structure(lexed, policy)
    projection = Projection(lexed, policy)
    consumed = tuple(change.span for change in structure.changes if change.rule_id != rule)
    changes, generated = symbol_changes(lexed, consumed)
    projection.apply(tuple(c for c in changes if c.rule_id != rule))
    projection.capture_tokens(generated)
    kept = [
        (c, owner)
        for c, owner in zip(structure.changes, structure.marker_ids, strict=True)
        if c.rule_id != rule
    ]
    omitted = {
        owner
        for c, owner in zip(structure.changes, structure.marker_ids, strict=True)
        if c.rule_id == rule and c.rule_id == "list.marker"
    }
    blocks = tuple(
        replace(b, parent_id=None) if b.parent_id in omitted else b
        for b in structure.blocks
        if b.id not in omitted
    )
    altered = replace(
        structure,
        blocks=blocks,
        changes=tuple(c for c, _ in kept),
        marker_ids=tuple(owner for _, owner in kept),
    )
    projection.markers(altered)
    projection.original_changes(_html_changes(lexed, altered))
    compact = lexed.document.source.field.value in policy.output.compact_fields
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
    final_blocks = tuple(replace(b, span=projection.block_span(b)) for b in blocks)
    annotations: list[Annotation] = []
    for token in generated:
        token_rule = _TOKEN_RULES[token.kind.value]
        if token_rule == rule:
            continue
        span = projection.token_span(token)
        annotations.append(
            Annotation(
                token.id,
                _TOKEN_KINDS[token.kind.value],
                token_rule,
                token.origin,
                token.payload,
                span,
                str(token.payload["rendered_token"]),
            )
        )
    return EvidenceView(
        lexed.document.source,
        projection.raw.text,
        final_blocks,
        tuple(annotations),
        "without:" + rule,
    )
