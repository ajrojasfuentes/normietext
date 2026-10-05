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
        constraints = root / "runtime-constraints.txt"
        subprocess.run(
            [
                "uv",
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--no-hashes",
                "--output-file",
                str(constraints),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(["uv", "venv", "--python", version, str(environment)], check=True)
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--constraint",
                str(constraints),
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
                "from importlib.util import find_spec; "
                "assert find_spec('evaluation') is None; "
                "assert find_spec('benchmarks') is None; "
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
                "from normietext import JobTextNormalizer; "
                "normalizer = JobTextNormalizer(); "
                "canonical = normalizer.canonicalize(lexed); "
                "assert canonical.text == 'C++'; "
                "assert normalizer.canonicalize(canonical) is canonical; "
                "result = normalizer.normalize_field(FieldInput("
                "JobField.JOB_DESCRIPTION, '🚀• Python\\n🇨🇷')); "
                "assert result.text == '- Python\\n[flag:CR]'; "
                "assert len(result.annotations) == 1; "
                "assert normalizer.canonicalize(result) is result; "
                "from normietext.operations import measure_field; "
                "measured = measure_field(normalizer, FieldInput(JobField.JOB_TITLE, 'Python')); "
                "assert measured.result.text == 'Python' and measured.error is None; "
                "assert measured.metrics['rules_version'] == '1.0.1'; "
                "assert canonical_bytes(manifest) == canonical_bytes(create_manifest()); "
                "import bs4, emoji, ftfy, lxml.etree, regex; "
                "print('Installed normietext', version('normietext'))",
            ],
            cwd=root,
            check=True,
        )


if __name__ == "__main__":
    main()
