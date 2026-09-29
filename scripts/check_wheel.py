"""Install the built wheel in isolation and verify it outside the checkout."""

import os
import subprocess
import tempfile
from pathlib import Path


def main() -> None:
    wheels = list(Path("dist").glob("*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"Expected exactly one wheel in dist, found {len(wheels)}")
    version = Path(".python-version").read_text(encoding="utf-8").strip()
    with tempfile.TemporaryDirectory(prefix="normietext-wheel-") as directory:
        root = Path(directory)
        environment = root / "venv"
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(["uv", "venv", "--python", version, str(environment)], check=True)
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--only-binary",
                "lxml",
                "--only-binary",
                "regex",
                "--python",
                str(python),
                str(wheels[0].resolve()),
            ],
            check=True,
        )
        subprocess.run(
            [
                str(python),
                "-I",
                "-c",
                "from importlib.metadata import version; "
                "from importlib.resources import files; "
                "import normietext, json, hashlib; "
                "from normietext import FieldInput, JobField, NormalizationPolicy; "
                "assert FieldInput(JobField.JOB_TITLE, 'Python').value == 'Python'; "
                "root = files(normietext).joinpath('data'); "
                "config = json.loads(root.joinpath('default_policy.json').read_bytes()); "
                "assert NormalizationPolicy.from_dict(config).limits.max_expansion_factor == 32; "
                "table_manifest = json.loads("
                "root.joinpath('unicode_policy_manifest.json').read_bytes()); "
                "assert all(hashlib.sha256(root.joinpath(name).read_bytes()).hexdigest() == digest "
                "for name, digest in table_manifest['files'].items()); "
                "assert files(normietext).joinpath('py.typed').is_file(); "
                "from normietext.manifest import create_manifest; "
                "from normietext.serialization import canonical_bytes; "
                "manifest = create_manifest(); "
                "assert manifest.code_revision.startswith('git:'); "
                "from normietext import SourceFormat; "
                "from normietext.adapters import convert_source, tracked_document; "
                "doc = convert_source(FieldInput(JobField.JOB_TITLE, 'C<b>++</b>', "
                "SourceFormat.HTML_FRAGMENT)); "
                "assert doc.text == 'C++' and doc.phase.value == 'converted'; "
                "assert tracked_document(doc).text == 'C++'; "
                "from normietext.stages.encoding import repair_document; "
                "from normietext.stages.lexing import lex_document; "
                "repaired = repair_document(doc); "
                "assert repaired.phase.value == 'repaired'; "
                "assert repair_document(repaired) is repaired; "
                "lexed = lex_document(repaired); "
                "assert lexed.phase.value == 'lexed' and lexed.document.text == 'C++'; "
                "assert lex_document(lexed) is lexed; "
                "assert canonical_bytes(manifest) == canonical_bytes(create_manifest()); "
                "import bs4, emoji, ftfy, lxml.etree, regex; "
                "print('Installed normietext', version('normietext'))",
            ],
            cwd=root,
            check=True,
        )


if __name__ == "__main__":
    main()
