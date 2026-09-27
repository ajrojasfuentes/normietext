import json
from dataclasses import fields, replace

import pytest

from normietext import (
    Annotation,
    AnnotationKind,
    FieldInput,
    FrozenMap,
    JobField,
    NormalizationPolicy,
    NormalizedField,
    Origin,
    OriginPrecision,
    SourceEvidence,
    Span,
)
from normietext.errors import (
    ModelValidationError,
    OutputInvariantError,
    PolicyMismatchError,
    ResourceLimitError,
)
from normietext.manifest import create_manifest, policy_hash
from normietext.serialization import _FIELDS, canonical_bytes, canonical_hash, to_data
from normietext.validation import validate_canonical, validate_text


@pytest.fixture(scope="module")
def manifest():
    return create_manifest()


def test_wire_contract_covers_every_explicit_model_member():
    for cls, names in _FIELDS.items():
        assert {f.name for f in fields(cls)} <= set(names.split()), cls
    policy = NormalizationPolicy()
    assert NormalizationPolicy.from_dict(to_data(policy)) == policy


def test_json_golden_unicode_order_and_sha256():
    value = {"z": [1, True, None], "a": "á"}
    assert canonical_bytes(value) == b'{"a":"\xc3\xa1","z":[1,true,null]}'
    assert canonical_hash({}) == "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
    assert canonical_bytes(FrozenMap.from_mapping(value)) == canonical_bytes(
        dict(reversed(list(value.items())))
    )
    for bad in (float("nan"), float("inf"), "\ud800", {1: "bad"}, {"value": object()}, {1, 2}):
        with pytest.raises(ModelValidationError):
            canonical_bytes(bad)
    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(ModelValidationError):
        canonical_bytes(cyclic)


def test_manifest_effective_versions_policy_changes_and_no_operational_fields(manifest):
    import unicodedata
    from importlib.metadata import version

    assert manifest.unicode_version == unicodedata.unidata_version
    assert dict(manifest.dependencies)["regex"] == version("regex")
    assert any(item.name == "lxml-build" for item in manifest.runtime_artifacts)
    assert any(item.name == "installed:lxml" for item in manifest.runtime_artifacts)
    assert manifest.code_revision.startswith("source-tree:")
    assert canonical_bytes(create_manifest()) == canonical_bytes(manifest)
    altered = replace(
        NormalizationPolicy(), limits=replace(NormalizationPolicy().limits, job_title=100)
    )
    assert policy_hash(altered) != manifest.policy_hash
    assert not {"timestamp", "duration", "hostname", "pid"} & set(
        json.loads(canonical_bytes(manifest))
    )
    with pytest.raises(ModelValidationError):
        create_manifest(require_wheels=True)


def test_annotation_order_and_payload_insertion_order_do_not_change_wire(manifest):
    source = SourceEvidence.from_input(FieldInput(JobField.JOB_TITLE, "x x"))
    annotations = tuple(
        Annotation(
            str(offset),
            AnnotationKind.LINK,
            "link",
            Origin(OriginPrecision.EXACT, Span(offset, offset + 1)),
            FrozenMap.from_mapping({"b": 2, "a": 1}),
            Span(offset, offset + 1),
        )
        for offset in (0, 2)
    )
    first = NormalizedField(source, "x x", manifest, annotations=annotations)
    second = replace(first, annotations=tuple(reversed(annotations)))
    assert canonical_bytes(first) == canonical_bytes(second)
    data = json.loads(canonical_bytes(first))
    assert data["phase"] == "canonical" and data["status"] == "ok" and data["field"] == "job_title"


@pytest.mark.parametrize(
    "text",
    [
        "a\u0301",
        "a  b",
        " a",
        "a ",
        "a\nb",
        "a\t",
        "a\u00a0b",
        "a\u200bb",
        "a\u2800b",
        "a\u2066b",
        "\ud800",
    ],
)
def test_canonical_validator_rejects_invalid_text_even_when_marked_canonical(text, manifest):
    with pytest.raises(OutputInvariantError):
        validate_text(text, compact=True)
    if "\ud800" not in text:
        source = SourceEvidence.from_input(FieldInput(JobField.JOB_TITLE, text))
        with pytest.raises(OutputInvariantError):
            validate_canonical(NormalizedField(source, text, manifest), expected_manifest=manifest)


def test_canonical_reuse_checks_manifest_references_and_limits(manifest):
    source = SourceEvidence.from_input(FieldInput(JobField.JOB_TITLE, "Python"))
    result = NormalizedField(source, "Python", manifest)
    assert validate_canonical(result, expected_manifest=manifest) is result
    for bad in (
        replace(manifest, policy_hash="0" * 64),
        replace(manifest, code_revision="other"),
        replace(manifest, unicode_version="other"),
    ):
        with pytest.raises(PolicyMismatchError):
            validate_canonical(replace(result, manifest=bad), expected_manifest=manifest)
    with pytest.raises(ResourceLimitError):
        validate_canonical(replace(result, text="x" * 1025), expected_manifest=manifest)
    from normietext import Block, BlockKind

    block = Block("b", BlockKind.LINE, Span(0, 6), Origin(OriginPrecision.EXACT, Span(0, 6)))
    corrupted = replace(result, blocks=(block,))
    object.__setattr__(block, "parent_id", "missing")
    with pytest.raises(OutputInvariantError):
        validate_canonical(corrupted, expected_manifest=manifest)


def test_reference_only_result_cannot_point_at_other_content(manifest):
    from normietext import ExtractionStatus, FieldOutcome, InputField

    source = FieldInput(JobField.JOB_TITLE, "abc", source_ref="ref")
    evidence = replace(SourceEvidence.from_input(source), raw=None, source_sha256="0" * 64)
    result = NormalizedField(evidence, "abc", manifest)
    with pytest.raises(ModelValidationError):
        FieldOutcome(InputField(JobField.JOB_TITLE, ExtractionStatus.PRESENT, source), result)


def test_actual_wheel_receipt_hashes_bytes_and_rejects_wrong_version(tmp_path):
    import hashlib
    from importlib.metadata import version
    from zipfile import ZipFile

    from normietext.manifest import wheel_artifact

    wheel = tmp_path / "example.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr("emoji.dist-info/METADATA", f"Name: emoji\nVersion: {version('emoji')}\n")
    receipt = wheel_artifact(wheel)
    assert receipt.name == "wheel:emoji"
    assert receipt.sha256 == hashlib.sha256(wheel.read_bytes()).hexdigest()
    with ZipFile(wheel, "w") as archive:
        archive.writestr("emoji.dist-info/METADATA", "Name: emoji\nVersion: 0.0.0\n")
    with pytest.raises(ModelValidationError):
        wheel_artifact(wheel)
