"""Validate fixture authoring and integrity, never claim normalization conformance."""

import hashlib
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures"


def load(path: Path) -> dict:
    return json.loads(path.read_bytes())


def test_normative_case_inventory_and_schema() -> None:
    corpus = load(FIXTURES / "regression/cases.json")
    schema = load(FIXTURES / "regression/schema.json")
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    validator.validate(corpus)
    assert {case["requirement"] for case in corpus["cases"]} == {f"T{i:02}" for i in range(1, 41)}
    assert len({case["id"] for case in corpus["cases"]}) == len(corpus["cases"])
    assert all(case["execution_status"] == "awaiting_normalizer" for case in corpus["cases"])
    by_id = {case["id"]: case for case in corpus["cases"]}
    assert by_id["T09"]["raw"] == "a\u200b\u0301"
    assert by_id["T36"]["raw"] == "\ud800"
    assert bytes.fromhex(by_id["T35-bytes"]["raw"]) == b"Python"
    assert by_id["T35-none"]["raw"] is None
    assert len(by_id["T37"]["raw"]) == 8193
    bad = {**corpus, "unknown": True}
    assert not validator.is_valid(bad)


def test_integral_matches_normative_fences_and_record_states() -> None:
    directory = FIXTURES / "integral/complex_multilingual_ai_role_001"
    fixture = load(directory / "fixture.json")
    Draft202012Validator(load(FIXTURES / "integral/schema.json")).validate(fixture)
    specification = (ROOT / "docs/normietext_v2.0_especificacion.md").read_bytes().decode("utf-8")
    for filename, metadata in fixture["files"].items():
        data = (directory / filename).read_bytes()
        assert hashlib.sha256(data).hexdigest() == metadata["sha256"]
        assert len(data) == metadata["bytes"]
        text = data.decode("utf-8")
        assert len(text) == metadata["codepoints"]
        section = specification.split("### " + metadata["spec_section"] + " ", 1)[1]
        fence = re.search(r"```text\n(.*?)\n```", section, re.S)
        assert fence and text == fence.group(1)
    assert [key for key, value in fixture["fields"].items() if value["state"] == "present"] == [
        "job_title",
        "job_description",
    ]
    assert sum(value["state"] == "missing" for value in fixture["fields"].values()) == 4
    raw = (directory / "job_description.raw.txt").read_bytes().decode("utf-8")
    assert "Flask   y" in raw and "pipelines  +" in raw
    assert re.search(r"^ {6}\S", raw, re.M)
    assert "¯\\_(ツ)_/¯" in raw and "\n\n\n" in raw
    expected = (directory / "job_description.expected.txt").read_bytes().decode("utf-8")
    assert expected.count("[flag:CR]") == 2
    assert expected.count("[emoji:") == 3
    assert (
        len(re.findall(r"^(?:- |\d+\. )", expected, re.M))
        == sum(item["count"] for item in fixture["expected_lists"])
        == 53
    )


def test_review_decisions_do_not_become_unsupported_goldens() -> None:
    inventory = load(FIXTURES / "review_inventory.json")["cases"]
    assert {item["id"] for item in inventory} == {f"T{i}" for i in range(41, 65)}
    decisions = {item["id"]: item["decision"] for item in inventory}
    assert decisions["T49"] == "rejected_use_negative"
    assert decisions["T54"] == "deferred_marker_extension"
    assert decisions["T56"] == "accepted_hint_without_inferred_list"
    supplemental = load(FIXTURES / "supplemental/cases.json")["cases"]
    assert any(case["decision_status"] == "pending_renderer" for case in supplemental)
    assert all(case["execution_status"] == "awaiting_normalizer" for case in supplemental)
    record = load(FIXTURES / "records/six_present.json")
    assert len(record["fields"]) == 6
    assert all(value["state"] == "present" for value in record["fields"].values())


def test_corpus_families_do_not_leak_between_splits() -> None:
    items = load(FIXTURES / "regression/cases.json")["cases"]
    items += load(FIXTURES / "supplemental/cases.json")["cases"]
    items += [
        load(FIXTURES / "records/six_present.json"),
        load(FIXTURES / "integral/complex_multilingual_ai_role_001/fixture.json"),
    ]
    families: dict[str, str] = {}
    for item in items:
        assert families.setdefault(item["family"], item["split"]) == item["split"]


def test_catalog_hashes_and_other_fixture_schemas() -> None:
    catalog = load(FIXTURES / "catalog.json")
    policy = catalog["configuration"]
    assert (
        hashlib.sha256((ROOT / policy["repository_path"]).read_bytes()).hexdigest()
        == policy["sha256"]
    )
    discovered = {
        str(path.relative_to(FIXTURES))
        for path in FIXTURES.rglob("*")
        if path.is_file()
        and path.suffix in (".json", ".txt", ".html")
        and path.name != "catalog.json"
    }
    assert discovered == set(catalog["files"])
    for name, digest in catalog["files"].items():
        assert hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest() == digest
    for data, schema in (
        ("supplemental/cases.json", "supplemental/schema.json"),
        ("records/six_present.json", "records/schema.json"),
        ("review_inventory.json", "review_inventory.schema.json"),
    ):
        definition = load(FIXTURES / schema)
        Draft202012Validator.check_schema(definition)
        Draft202012Validator(definition).validate(load(FIXTURES / data))
    cases = load(FIXTURES / "regression/cases.json")["cases"]
    assert next(c for c in cases if c["id"] == "T14")["raw"].count("\r\n") == 4
