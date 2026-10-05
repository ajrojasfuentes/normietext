"""Batch capacity on the supplied synthetic corpus, using bounded ordered processes."""

import argparse
import hashlib
import json
import multiprocessing
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from benchmarks.adversarial import load_samples
from benchmarks.load import distribution, environment
from evaluation.quality import span_errors
from normietext import JobTextNormalizer
from normietext.operations import measure_record
from normietext.serialization import canonical_bytes

# Manual evidence anchors from raw, not derived from normalized output or semantic labels.
ANCHORS = {
    0: ("NOT a pure Data Scientist role", "$4,500", "$7,250", "₡2,400,000+"),
    1: ("Customer contract value: $450,000/year", "NOT salary", "Do NOT infer valuation"),
}
_NORMALIZER: JobTextNormalizer | None = None


def process(index: int) -> dict[str, Any]:
    global _NORMALIZER
    if _NORMALIZER is None:
        _NORMALIZER = JobTextNormalizer()
    sample = load_samples()[index]
    measurement = measure_record(_NORMALIZER, sample.record)
    result = measurement.result
    errors = []
    if result is None:
        errors.append(str(measurement.error))
    else:
        for item in result.fields:
            if item.failure:
                errors.append(item.failure.code.value)
            if item.result:
                errors.extend(span_errors(item.result))
                assert item.input.source is not None
                if item.result.source.raw != item.input.source.value:
                    errors.append("source_changed")
        description = result.fields[1].result
        anchors = ANCHORS.get(
            index,
            (
                "This job is NOT automatically part-time",
                "Nearby numbers that are NOT necessarily salary:",
            ),
        )
        if description is None or any(anchor not in description.text for anchor in anchors):
            errors.append("missing_manual_evidence")
    rss: int | None = None
    # resource is Unix-only; keep unavailable RSS distinct from a zero reading.
    if sys.platform != "win32":
        try:
            import resource

            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (
                1 if sys.platform == "darwin" else 1024
            )
        except ImportError:
            pass
    return {
        "name": sample.name,
        "input_sha256": sample.sha256,
        "output_sha256": hashlib.sha256(canonical_bytes(result)).hexdigest(),
        "metrics": json.loads(canonical_bytes(measurement.metrics)),
        "errors": errors,
        "process_peak_rss_bytes": rss,
    }


def run(workers: int, rounds: int) -> dict[str, Any]:
    # Ordered map, fixed chunksize and small submitted inventory bound queued work.
    indices = list(range(20)) * rounds
    start = time.perf_counter()
    if workers == 1:
        results = [process(i) for i in indices]
    else:
        with ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        ) as pool:
            results = list(pool.map(process, indices, chunksize=1))
    duration = time.perf_counter() - start
    failures = [r["name"] for r in results if r["errors"]]
    signatures: dict[str, str] = {}
    replay = True
    for result in results:
        replay &= (
            signatures.setdefault(result["name"], result["output_sha256"])
            == result["output_sha256"]
        )
    return {
        "workers": workers,
        "rounds": rounds,
        "records": len(results),
        "wall_seconds_including_startup_io_and_checks": duration,
        "records_per_second": len(results) / duration,
        "projected_100000_hours": duration / len(results) * 100000 / 3600,
        "latency_seconds": distribution([r["metrics"]["elapsed_seconds"] for r in results]),
        "failures": failures,
        "replay_equal": replay,
        "output_hashes": signatures,
        "process_peak_rss_bytes": max(
            (r["process_peak_rss_bytes"] or 0 for r in results), default=0
        )
        or None,
        "observations": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 2, 4])
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--output", type=Path, default=Path("/tmp/normietext-batch.json"))
    args = parser.parse_args()
    if args.rounds < 1 or args.rounds > 100 or any(w < 1 or w > 32 for w in args.workers):
        parser.error("Use 1..100 rounds and 1..32 processes")
    results = []
    for workers in args.workers:
        result = run(workers, args.rounds)
        results.append(result)
        print(
            f"workers={workers} records/s={result['records_per_second']:.3f} "
            f"failures={len(result['failures'])}",
            flush=True,
        )
    report = {
        "schema_version": "1.0.0",
        "environment": environment(),
        "cohort": "user_synthetic_adversarial_20",
        "runs": results,
        "cross_worker_replay_equal": all(
            r["output_hashes"] == results[0]["output_hashes"] for r in results
        ),
        "limitations": [
            "Repeated public synthetic inputs, not 100000 distinct jobs",
            "100000-hour estimate is extrapolated, not an executed full batch",
            "seniority is missing; partial records without failed fields are expected",
            "modality retained in ingestion sidecar, outside six-field normalizer",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if (
        any(r["failures"] or not r["replay_equal"] for r in results)
        or not report["cross_worker_replay_equal"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
