"""Run with an isolated wheel interpreter: downstream evidence consumer and replay."""

import hashlib
import json
import sys
from pathlib import Path

from normietext import (
    ExtractionStatus,
    FieldInput,
    InputField,
    JobField,
    JobInputRecord,
    JobTextNormalizer,
)
from normietext.serialization import canonical_bytes


def main() -> None:
    root = Path(sys.argv[1])
    output = Path(sys.argv[2])
    n = JobTextNormalizer()
    mapping = {
        "job_title": "title",
        "job_description": "description",
        "job_criteria_list": "criteria_list",
        "job_type": "type",
        "raw_location": "location",
    }
    results = []
    for path in sorted(root.glob("adversarial_linkedin_job-*.json")):
        original = path.read_bytes()
        data = json.loads(original)
        fields = []
        for field in JobField:
            key = mapping.get(field.value)
            if key is None:
                fields.append(InputField(field, ExtractionStatus.MISSING))
            else:
                raw = "\n".join(data[key]) if key == "criteria_list" else data[key]
                fields.append(InputField(field, ExtractionStatus.PRESENT, FieldInput(field, raw)))
        result = n.normalize_record(JobInputRecord(tuple(fields)), strict=True)
        assert all(item.result is not None for item in result.fields if item.input.source)
        values = []
        for item in result.fields:
            if item.result is not None:
                assert n.canonicalize(item.result) is item.result
                assert item.input.source is not None
                assert item.result.source.raw == item.input.source.value
                # A minimal downstream consumer preserves context and canonical offsets.
                candidates = []
                for signal in ("NOT", "USD", "CAD", "Python", "salary"):
                    start = 0
                    while (position := item.result.text.find(signal, start)) >= 0:
                        candidates.append(
                            {"signal": signal, "span": [position, position + len(signal)]}
                        )
                        start = position + len(signal)
                payload = json.loads(canonical_bytes(item.result))
                payload.pop("manifest")
                values.append(
                    {"field": item.field.value, "canonical": payload, "candidates": candidates}
                )
        results.append(
            {
                "name": path.name,
                "source_sha256": hashlib.sha256(original).hexdigest(),
                "values_sha256": hashlib.sha256(canonical_bytes(values)).hexdigest(),
            }
        )
    if len(results) != 20:
        raise ValueError("Expected all 20 jobs")
    output.write_text(json.dumps(results, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
