"""Explicit operational wrappers. Export only metrics; results/traces contain source data."""

import hashlib
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter

from normietext._telemetry import StageCapture, capture
from normietext.api import JobTextNormalizer
from normietext.errors import ErrorCode, NormalizationError
from normietext.models import (
    FieldInput,
    FrozenMap,
    JobInputRecord,
    NormalizedField,
    NormalizedJobRecord,
)
from normietext.serialization import canonical_hash


@dataclass(frozen=True, slots=True)
class Measurement[T]:
    result: T | None
    error: ErrorCode | None
    metrics: FrozenMap
    # Explicit debug access only. Never include these in logs or metrics export.
    trace: tuple[tuple[str, object], ...] = ()


def _field_metrics(source: FieldInput, result: NormalizedField | None) -> dict[str, object]:
    metrics: dict[str, object] = {
        "field": source.field.value,
        "format": source.source_format.value,
        # Scraper version is caller-controlled: hash to avoid leaking arbitrary content.
        "scraper_version_sha256": hashlib.sha256(
            (source.source_adapter_version or "").encode()
        ).hexdigest(),
        "input_codepoints": len(source.value),
        "empty_before": not source.value,
    }
    if result is not None:
        metrics.update(
            manifest_id=canonical_hash(result.manifest),
            status=result.status.value,
            output_codepoints=len(result.text),
            empty_after=not result.text,
            length_ratio=len(result.text) / len(source.value) if source.value else None,
            edits_by_rule=dict(Counter(edit.rule_id for edit in result.edits)),
            annotations_by_kind=dict(Counter(a.kind.value for a in result.annotations)),
            issues_by_code=dict(Counter(i.code.value for i in result.issues)),
            edits_by_precision=dict(Counter(e.origin.precision.value for e in result.edits)),
            origins_by_precision=dict(
                Counter(b.origin.precision.value for b in result.blocks)
                + Counter(a.origin.precision.value for a in result.annotations)
                + Counter(e.origin.precision.value for e in result.edits)
            ),
            hints=sum(a.kind.value == "emoji_hint" for a in result.annotations),
            repairs=sum(e.rule_id == "encoding.fix_encoding" for e in result.edits),
            # Counts of attributed operations, not guessed character deletions.
            removals=sum(e.rule_id in {"emoji.remove", "unicode.invisible"} for e in result.edits),
        )
    return metrics


def _measure[T](
    function: Callable[[], T], normalizer: JobTextNormalizer, *, trace: bool
) -> tuple[T | None, ErrorCode | None, dict[str, object], StageCapture]:
    if type(trace) is not bool:
        raise TypeError("trace must be boolean")
    active = StageCapture(capture_trace=trace)
    token = capture.set(active)
    start = perf_counter()
    result, error = None, None
    try:
        result = function()
    except NormalizationError as exc:
        error = exc.code
    finally:
        elapsed = perf_counter() - start
        capture.reset(token)
    metrics: dict[str, object] = {
        "profile": normalizer.policy.policy_id,
        "rules_version": normalizer.policy.normalization_version,
        "elapsed_seconds": elapsed,
        "stage_seconds": active.timings,
        "error": error.value if error else None,
        "timeout": error is ErrorCode.REGEX_TIMEOUT,
    }
    return result, error, metrics, active


def measure_field(
    normalizer: JobTextNormalizer, source: FieldInput, *, trace: bool = False
) -> Measurement[NormalizedField]:
    """Measure one call; typed failures have result=None and retain only an error code.

    No logs, callbacks, network, or persistent global collectors. Ordinary API calls
    continue to raise normally. Unexpected implementation exceptions propagate.
    Rejected non-FieldInput values retain INVALID_TYPE without source dimensions.
    """
    result, error, metrics, active = _measure(
        lambda: normalizer.normalize_field(source), normalizer, trace=trace
    )
    if isinstance(source, FieldInput):
        metrics.update(_field_metrics(source, result))
    return Measurement(result, error, FrozenMap.from_mapping(metrics), tuple(active.snapshots))


def measure_record(
    normalizer: JobTextNormalizer, record: JobInputRecord, *, trace: bool = False
) -> Measurement[NormalizedJobRecord]:
    """Measure the public non-strict record path, preserving all six outcomes."""
    result, error, metrics, active = _measure(
        lambda: normalizer.normalize_record(record), normalizer, trace=trace
    )
    fields: list[dict[str, object]] = []
    if result is not None:
        metrics.update(status=result.status.value, partial=result.status.value == "partial")
        for outcome in result.fields:
            entry: dict[str, object] = (
                _field_metrics(outcome.input.source, outcome.result)
                if outcome.input.source is not None
                else {"field": outcome.field.value}
            )
            entry["extraction_state"] = outcome.input.state.value
            entry["error"] = outcome.failure.code.value if outcome.failure else None
            entry["timeout"] = bool(
                outcome.failure and outcome.failure.code is ErrorCode.REGEX_TIMEOUT
            )
            fields.append(entry)
    metrics["fields"] = fields
    return Measurement(result, error, FrozenMap.from_mapping(metrics), tuple(active.snapshots))
