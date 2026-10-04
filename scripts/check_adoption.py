"""Exercise candidate -> rollback -> candidate from original sources in isolated installs."""

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--rollback", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    wheels = [args.candidate.resolve(), args.rollback.resolve(), args.candidate.resolve()]
    observations = []
    with tempfile.TemporaryDirectory(prefix="normietext-adoption-") as temp:
        directory = Path(temp)
        subprocess.run(
            [
                "uv",
                "venv",
                "--python",
                (ROOT / ".python-version").read_text().strip(),
                str(directory / "venv"),
            ],
            check=True,
        )
        python = directory / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        for index, wheel in enumerate(wheels):
            subprocess.run(
                [
                    "uv",
                    "pip",
                    "install",
                    "--reinstall-package",
                    "normietext",
                    "--python",
                    str(python),
                    str(wheel),
                ],
                check=True,
            )
            output = directory / f"probe-{index}.json"
            subprocess.run(
                [
                    str(python),
                    "-I",
                    str(ROOT / "scripts/consumer_probe.py"),
                    str(ROOT / "benchmarks/cases/adversarial_linkedin_jobs_20"),
                    str(output),
                ],
                cwd=directory,
                check=True,
            )
            observations.append(
                {
                    "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                    "results": json.loads(output.read_bytes()),
                }
            )
    report = {
        "schema_version": "1.0.0",
        "sequence": ["candidate", "rollback", "candidate"],
        "synthetic_consumer": True,
        "observations": observations,
        "replay_equal": observations[0]["results"] == observations[2]["results"],
        "shadow_equal": observations[0]["results"] == observations[1]["results"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    if not report["replay_equal"] or not report["shadow_equal"]:
        raise SystemExit("Consumer output changed: review before promotion")


if __name__ == "__main__":
    main()
