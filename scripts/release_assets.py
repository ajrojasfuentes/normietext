"""Prepare checksums for the two verified distributions; never rebuild or publish."""

import argparse
import hashlib
from pathlib import Path


def checksums(directory: Path) -> Path:
    wheels = sorted(directory.glob("*.whl"))
    sources = sorted(directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise ValueError("Require exactly one verified wheel and one sdist")
    result = directory / "SHA256SUMS"
    result.write_text(
        "".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in (*wheels, *sources)
        ),
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(checksums(args.directory))


if __name__ == "__main__":
    main()
