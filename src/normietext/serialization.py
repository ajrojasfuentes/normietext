"""Explicit canonical JSON contract (UTF-8, sorted keys, no implicit dataclass wire API)."""

import hashlib
import json
from enum import StrEnum

from normietext import models, policy
from normietext._validation import require, valid_text

# Adding a model member requires a deliberate wire-contract review here.
_FIELDS: dict[type[object], str] = {
    models.AlignmentSegment: "output origin linear",
    models.Span: "start end",
    models.FieldInput: "field value source_format source_ref source_adapter_version",
    models.ExtractionError: "code message source_ref",
    models.InputField: "field state source error",
    models.JobInputRecord: "fields",
    models.SourceEvidence: (
        "field source_format source_length raw source_ref source_adapter_version source_sha256"
    ),
    models.Origin: "precision span source_block_id",
    models.Block: (
        "id kind span origin parent_id list_id ordinal depth row column rowspan colspan "
        "heading_level origin_tag header metadata"
    ),
    models.Association: "id term_ids definition_ids origin source_contract parent_id",
    models.Annotation: "id kind rule_id origin payload span rendered_token",
    models.Edit: "id rule_id origin replacement",
    models.Issue: "code rule_id origin details",
    models.VersionedArtifact: "name version sha256",
    models.Manifest: (
        "schema_version normalization_version policy_id policy_hash code_revision python_version "
        "unicode_version backend libxml2_version dependencies tables runtime_artifacts"
    ),
    models.ParsedDocument: (
        "source text phase blocks associations annotations edits issues alignment"
    ),
    models.NormalizedField: (
        "field source_format source text status phase manifest blocks associations "
        "annotations edits issues"
    ),
    models.FieldFailure: "source code message",
    models.FieldOutcome: "field input result failure",
    models.NormalizedJobRecord: "status fields",
    policy.NormalizationPolicy: (
        "policy_id schema_version normalization_version input encoding unicode emoji whitespace "
        "punctuation structure output limits"
    ),
    policy.InputPolicy: (
        "default_format auto_detect_html require_recoverable_source reject_surrogates"
    ),
    policy.EncodingPolicy: (
        "operation restore_byte_a0 replace_lossy_sequences decode_inconsistent_utf8 fix_c1_controls"
    ),
    policy.UnicodePolicy: (
        "normalization final_normalization remove_cf remove_default_ignorables remove_cc_except_lf "
        "remove_braille_blank"
    ),
    policy.EmojiPolicy: (
        "default_action region_flags subdivision_flags hints protected_text_symbols keycaps"
    ),
    policy.WhitespacePolicy: (
        "horizontal collapse_runs strip_each_line preserve_indentation max_blank_lines strip_field"
    ),
    policy.PunctuationPolicy: (
        "global_dash_folding global_quote_folding fullwidth_solidus_in_ordinary_text"
    ),
    policy.StructurePolicy: "plain_text_lists_in preserve_ordinals metadata_before_spacing",
    policy.OutputPolicy: (
        "compact_fields multiline_fields generated_tokens_require_annotations trace_snapshots"
    ),
    policy.ResourceLimits: (
        "job_title job_description job_criteria_list job_type seniority raw_location record "
        "html_nodes structural_depth output_floor max_expansion_factor regex_timeout_ms"
    ),
}


def _origin_key(item: models.Annotation | models.Edit | models.Issue) -> tuple[object, ...]:
    origin = item.origin
    position = origin.span
    final = item.span if isinstance(item, models.Annotation) else None
    return (
        origin.source_block_id or "",
        position.start if position else -1,
        position.end if position else -1,
        origin.precision.value,
        final.start if final else -1,
        final.end if final else -1,
        item.rule_id,
        item.code.value if isinstance(item, models.Issue) else item.id,
        canonical_bytes(item),
    )


def to_data(value: object, *, _depth: int = 0) -> object:
    """Return detached JSON data; preserve semantic sequence order, sort unordered collections."""
    require(_depth <= 64, "Serialization nesting exceeds 64")
    if value is None or type(value) in (bool, int):
        return value
    if isinstance(value, StrEnum):
        return value.value
    if type(value) is str:
        require(valid_text(value), "Cannot serialize isolated surrogates")
        return value
    if type(value) is float:
        models.freeze_json(value)  # Reject NaN/Infinity, including nested payloads.
        return value
    if isinstance(value, (models.FrozenMap, dict)):
        require(all(type(key) is str and valid_text(key) for key in value), "Invalid JSON key")
        return {key: to_data(item, _depth=_depth + 1) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [to_data(item, _depth=_depth + 1) for item in value]
    names = _FIELDS.get(type(value))
    require(names is not None, "Unsupported canonical serialization type")
    assert names is not None
    result: dict[str, object] = {}
    for name in names.split():
        item = getattr(value, name)
        if name in ("annotations", "edits", "issues"):
            item = tuple(sorted(item, key=_origin_key))
        elif isinstance(value, models.Manifest) and name in ("tables", "runtime_artifacts"):
            item = tuple(sorted(item, key=lambda artifact: artifact.name))
        elif isinstance(value, models.Manifest) and name == "dependencies":
            item = tuple(sorted(item))
        result[name] = to_data(item, _depth=_depth + 1)
    return result


def canonical_bytes(value: object) -> bytes:
    """No normalization, timestamps, platform newlines, ASCII escaping or nonfinite numbers."""
    return json.dumps(
        to_data(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8", errors="strict")


def canonical_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
