"""Explicit ingestion of the user-supplied synthetic set; no semantic truth inference."""

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from normietext import (
    ExtractionStatus,
    FieldInput,
    InputField,
    JobField,
    JobInputRecord,
    SourceFormat,
)

ROOT = Path(__file__).resolve().parent / "cases/adversarial_linkedin_jobs_20"
MAPPING = {
    JobField.JOB_TITLE: "title",
    JobField.JOB_DESCRIPTION: "description",
    JobField.JOB_CRITERIA_LIST: "criteria_list",
    JobField.JOB_TYPE: "type",
    JobField.RAW_LOCATION: "location",
}


@dataclass(frozen=True)
class Sample:
    name: str
    original_json: bytes
    record: JobInputRecord
    modality: str
    criteria_items: tuple[str, ...]

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.original_json).hexdigest()


@lru_cache(maxsize=1)
def load_samples() -> tuple[Sample, ...]:
    result = []
    for path in sorted(ROOT.glob("adversarial_linkedin_job-*.json")):
        original = path.read_bytes()
        data = json.loads(original)
        if set(data) != {"title", "description", "criteria_list", "type", "location", "modality"}:
            raise ValueError("Unexpected sample keys")
        if any(type(data[k]) is not str for k in data if k != "criteria_list"):
            raise ValueError("Expected literal strings")
        criteria = data["criteria_list"]
        if type(criteria) is not list or any(type(item) is not str for item in criteria):
            raise ValueError("Expected criteria strings")
        entries = []
        for field in JobField:
            key = MAPPING.get(field)
            if key is None:
                entries.append(InputField(field, ExtractionStatus.MISSING))
                continue
            raw = "\n".join(criteria) if key == "criteria_list" else data[key]
            entries.append(
                InputField(
                    field,
                    ExtractionStatus.PRESENT,
                    FieldInput(
                        field,
                        raw,
                        SourceFormat.PLAIN_TEXT,
                        source_ref=f"synthetic:{path.name}#{key}",
                        source_adapter_version="adversarial-json-v1",
                    ),
                )
            )
        result.append(
            Sample(
                path.stem,
                original,
                JobInputRecord(tuple(entries)),
                data["modality"],
                tuple(criteria),
            )
        )
    if len(result) != 20:
        raise ValueError("Expected exactly 20 user samples")
    return tuple(result)
