"""Reject a release tag that does not match the package version."""

import os
import tomllib
from pathlib import Path


def main() -> None:
    with Path("pyproject.toml").open("rb") as stream:
        version = tomllib.load(stream)["project"]["version"]
    tag = os.environ["RELEASE_TAG"]
    if tag != f"v{version}":
        raise SystemExit(f"Release tag {tag!r} does not match package version v{version}")


if __name__ == "__main__":
    main()
