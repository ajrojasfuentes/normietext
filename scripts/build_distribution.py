"""Build in a temporary source tree, embedding Git revision and exact code fingerprint."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from normietext.manifest import code_fingerprint


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root))
    digest = code_fingerprint()
    info = {
        "schema_version": "1.0.0",
        "code_sha256": digest,
        "code_revision": "git:" + revision + ("+tree:" + digest if dirty else ""),
    }
    epoch = subprocess.check_output(
        ["git", "show", "-s", "--format=%ct", "HEAD"], cwd=root, text=True
    ).strip()
    with tempfile.TemporaryDirectory(prefix="normietext-build-") as temporary:
        stage = Path(temporary)
        for name in ("pyproject.toml", "README.md", "LICENSE", "uv.lock", ".python-version"):
            shutil.copy2(root / name, stage / name)
        shutil.copytree(
            root / "src", stage / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
        (stage / "src/normietext/data/build_info.json").write_text(
            json.dumps(info, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        env = dict(os.environ, SOURCE_DATE_EPOCH=epoch)
        subprocess.run(
            ["uv", "build", "--project", str(stage), "--out-dir", str(root / "dist")],
            cwd=stage,
            env=env,
            check=True,
        )


if __name__ == "__main__":
    main()
