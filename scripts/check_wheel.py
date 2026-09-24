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
            ["uv", "pip", "install", "--python", str(python), str(wheels[0].resolve())],
            check=True,
        )
        subprocess.run(
            [
                str(python),
                "-I",
                "-c",
                "from importlib.metadata import version; "
                "from importlib.resources import files; "
                "import normietext; "
                "assert files(normietext).joinpath('py.typed').is_file(); "
                "import bs4, emoji, ftfy, lxml.etree, regex; "
                "print('Installed normietext', version('normietext'))",
            ],
            cwd=root,
            check=True,
        )


if __name__ == "__main__":
    main()
