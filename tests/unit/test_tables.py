import hashlib
import json
from importlib.resources import files

from jsonschema import Draft202012Validator

import normietext
from normietext.policy import NormalizationPolicy


def test_tables_are_packaged_licensed_and_hash_verified() -> None:
    root = files(normietext).joinpath("data")
    manifest = json.loads(root.joinpath("unicode_policy_manifest.json").read_bytes())
    for name, digest in manifest["files"].items():
        assert hashlib.sha256(root.joinpath(name).read_bytes()).hexdigest() == digest
    assert {
        "licenses/Unicode-3.0.txt",
        "licenses/emoji-LICENSE.txt",
        "licenses/regex-LICENSE.txt",
    } <= set(manifest["files"])
    assert manifest["classification_unicode_version"] == "17.0.0"
    assert manifest["normalization_unicode_version"] == "16.0.0"
    for name in ("emoji_hints", "region_sequences", "kaomoji", "unicode_properties"):
        schema = json.loads(root.joinpath(name + ".schema.json").read_bytes())
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(
            json.loads(root.joinpath(name + ".json").read_bytes())
        )


def test_tables_cover_explicit_symbols_and_disjoint_ranges() -> None:
    root = files(normietext).joinpath("data")
    hints = json.loads(root.joinpath("emoji_hints.json").read_bytes())["entries"]
    assert {item["id"] for item in hints} == {
        "money_bag",
        "round_pushpin",
        "warning",
        "check_mark_button",
        "cross_mark",
    }
    assert len(hints) == len({item["sequence"] for item in hints}) == 15
    assert max(len(item["token"]) + 1 for item in hints) == 26
    regions = json.loads(root.joinpath("region_sequences.json").read_bytes())["entries"]
    assert {"CR", "EU", "UN"} <= {item["code"] for item in regions}
    assert {item["code"] for item in regions if item["kind"] == "subdivision"} == {
        "gbeng",
        "gbsct",
        "gbwls",
    }
    properties = json.loads(root.joinpath("unicode_properties.json").read_bytes())["entries"]
    for ranges in properties.values():
        previous_end = -1
        for start, end in ranges:
            assert 0 <= start < end <= 0x110000 and start > previous_end
            previous_end = end
    assert any(start <= 0x200D < end for start, end in properties["Cf"])
    assert any(start <= 0xFE0F < end for start, end in properties["Default_Ignorable_Code_Point"])


def test_default_configuration_matches_schema_and_python_contract() -> None:
    root = files(normietext).joinpath("data")
    data = json.loads(root.joinpath("default_policy.json").read_bytes())
    schema = json.loads(root.joinpath("policy.schema.json").read_bytes())
    validator = Draft202012Validator(schema)
    validator.validate(data)
    assert NormalizationPolicy.from_dict(data) == NormalizationPolicy()
    assert not validator.is_valid({**data, "unknown": 1})
