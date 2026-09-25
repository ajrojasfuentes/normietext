"""Offline regeneration of profile tables from the pinned, licensed dependencies.

No network calls. --check compares byte-for-byte without updating tracked files.
"""

import argparse
import hashlib
import json
from importlib.metadata import distribution, version
from pathlib import Path

import emoji
import regex

ROOT = Path(__file__).resolve().parents[1] / "src/normietext/data"


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def artifacts() -> dict[str, bytes]:
    if version("emoji") != "2.16.0" or version("regex") != "2026.9.10":
        raise SystemExit("Regeneration requires the pinned emoji and regex versions")
    result: dict[str, bytes] = {}
    hints = []
    for base, name in [
        ("💰", "money_bag"),
        ("📍", "round_pushpin"),
        ("⚠", "warning"),
        ("✅", "check_mark_button"),
        ("❌", "cross_mark"),
    ]:
        for suffix in ("", "\ufe0e", "\ufe0f"):
            hints.append({"sequence": base + suffix, "id": name, "token": f"[emoji:{name}]"})
    regions = []
    for seq in sorted(emoji.EMOJI_DATA):
        if len(seq) == 2 and all(0x1F1E6 <= ord(c) <= 0x1F1FF for c in seq):
            code = "".join(chr(ord(c) - 0x1F1E6 + 65) for c in seq)
            regions.append(
                {"sequence": seq, "code": code, "kind": "region", "token": f"[flag:{code}]"}
            )
        elif seq.startswith("🏴\U000e0067") and seq.endswith("\U000e007f"):
            code = "".join(chr(ord(c) - 0xE0000) for c in seq[1:-1])
            regions.append(
                {
                    "sequence": seq,
                    "code": code,
                    "kind": "subdivision",
                    "token": f"[flag-subdivision:{code}]",
                }
            )
    # Indices equal codepoints; property matches exclude surrogate codepoints.
    scalars = "".join(map(chr, range(0x110000)))
    properties = {}
    for prop in (
        "Cf",
        "Cc",
        "Default_Ignorable_Code_Point",
        "Extended_Pictographic",
        "Emoji_Modifier",
    ):
        properties[prop] = [
            [m.start(), m.end()]
            for m in regex.finditer(
                rf"\p{{{prop}}}+",
                scalars,
                flags=regex.VERSION1 | regex.UNICODE,
            )
        ]
    catalogs: dict[str, object] = {
        "emoji_hints.json": hints,
        "region_sequences.json": regions,
        "kaomoji.json": ["¯\\_(ツ)_/¯", "ಠ_ಠ", "(ಥ\ufe4fಥ)"],
        "unicode_properties.json": properties,
    }
    for filename, entries in catalogs.items():
        authority = (
            "regex/2026.9.10; Unicode 17.0.0"
            if filename.startswith("unicode")
            else "emoji/2.16.0"
            if filename.startswith("region")
            else "normietext specification"
        )
        license_id = (
            "Unicode-3.0"
            if filename.startswith("unicode")
            else "BSD-3-Clause AND Unicode-3.0"
            if filename.startswith("region")
            else "MIT"
        )
        result[filename] = encoded(
            {
                "schema_version": "1.0.0",
                "table_version": "1.0.0",
                "authority": authority,
                "license": license_id,
                "entries": entries,
            }
        )
    # Preserve the complete notices shipped by upstream rather than paraphrasing them.
    for package in ("emoji", "regex"):
        dist = distribution(package)
        for file in dist.files or ():
            if ".dist-info/licenses/" in str(file) and file.name.lower().startswith("license"):
                result[f"licenses/{package}-{file.name}"] = Path(
                    str(dist.locate_file(file))
                ).read_bytes()
    result["licenses/Unicode-3.0.txt"] = (ROOT / "licenses/Unicode-3.0.txt").read_bytes()
    result["unicode_policy_manifest.json"] = encoded(
        {
            "schema_version": "1.0.0",
            "table_version": "1.0.0",
            "classification_unicode_version": "17.0.0",
            "normalization_authority": "CPython unicodedata",
            "normalization_unicode_version": "16.0.0",
            "generator": "scripts/generate_tables.py",
            "dependencies": {"emoji": "2.16.0", "regex": "2026.9.10"},
            "files": {
                name: hashlib.sha256(data).hexdigest() for name, data in sorted(result.items())
            },
        }
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, data in artifacts().items():
        path = ROOT / name
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                raise SystemExit(f"Table differs: {name}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print("Profile tables verified" if args.check else "Profile tables generated")


if __name__ == "__main__":
    main()
