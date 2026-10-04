"""Isolated, reproducible load harness. No timing assertions in shared-runner tests."""

import argparse
import cProfile
import hashlib
import io
import json
import math
import os
import platform
import pstats
import statistics
import subprocess
import sys
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from normietext import (
    ExtractionStatus,
    FieldInput,
    InputField,
    JobField,
    JobInputRecord,
    JobTextNormalizer,
    SourceFormat,
)
from normietext.manifest import create_manifest
from normietext.operations import Measurement, measure_field, measure_record
from normietext.serialization import canonical_bytes

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Workload:
    name: str
    cohort: str
    source: FieldInput | JobInputRecord


def workloads() -> tuple[Workload, ...]:
    d = JobField.JOB_DESCRIPTION
    integral = ROOT / "tests/fixtures/integral/complex_multilingual_ai_role_001"
    record_data = json.loads((ROOT / "tests/fixtures/records/six_present.json").read_bytes())
    record = JobInputRecord(
        tuple(
            InputField(
                f,
                ExtractionStatus.PRESENT,
                FieldInput(
                    f,
                    record_data["fields"][f.value]["raw"],
                    SourceFormat(record_data["fields"][f.value]["source_format"]),
                ),
            )
            for f in JobField
        )
    )
    return (
        Workload("six_fields", "synthetic_representative", record),
        Workload(
            "integral",
            "synthetic_representative",
            FieldInput(d, (integral / "job_description.raw.txt").read_bytes().decode()),
        ),
        Workload(
            "compact",
            "synthetic_representative",
            FieldInput(JobField.JOB_TITLE, "  Senior Python\uff0fC++ Engineer 🇨🇷  "),
        ),
        Workload(
            "escaped",
            "synthetic_representative",
            FieldInput(
                d,
                "Python &amp; C++\nNOT remote &lt;b&gt;literal&lt;/b&gt;",
                SourceFormat.HTML_ESCAPED_TEXT,
            ),
        ),
        Workload(
            "html",
            "synthetic_representative",
            FieldInput(
                d,
                "<h2>Skills</h2><ul><li>Python</li><li>C++</li></ul>"
                "<table><tr><td>A</td><td></td><td></td><td>B</td></tr></table>",
                SourceFormat.HTML_FRAGMENT,
            ),
        ),
        Workload("max_plain", "adversarial", FieldInput(d, "x" * 262144)),
        Workload("combining", "adversarial", FieldInput(d, "a\u0301" * 2048)),
        Workload("hints_2000", "adversarial", FieldInput(d, "✅" * 2000)),
        Workload("url_near_miss", "adversarial", FieldInput(d, "a." * 8192 + "@")),
        Workload(
            "html_depth",
            "adversarial",
            FieldInput(d, "<div>" * 128 + "X" + "</div>" * 128, SourceFormat.HTML_FRAGMENT),
        ),
        Workload(
            "html_nodes", "adversarial", FieldInput(d, "<br>" * 19998, SourceFormat.HTML_FRAGMENT)
        ),
        Workload(
            "html_depth_rejected",
            "adversarial",
            FieldInput(d, "<div>" * 129 + "X" + "</div>" * 129, SourceFormat.HTML_FRAGMENT),
        ),
    )


def distribution(values: list[float]) -> dict[str, float | int]:
    ordered = sorted(values)
    return {
        "samples": len(values),
        "min": ordered[0],
        "max": ordered[-1],
        "mean": statistics.mean(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0,
        **{f"p{p}": ordered[math.ceil(len(ordered) * p / 100) - 1] for p in (50, 95, 99)},
    }


def run_case(
    case: Workload,
    warmup: int,
    repetitions: int,
    *,
    python_memory: bool = False,
    profile_enabled: bool = False,
) -> dict[str, Any]:
    normalizer = JobTextNormalizer()
    source = case.source

    def run() -> Measurement[Any]:
        if isinstance(source, FieldInput):
            return measure_field(normalizer, source)
        return measure_record(normalizer, source)

    cold_start = time.perf_counter()
    first = run()
    cold = time.perf_counter() - cold_start
    for _ in range(warmup):
        run()
    elapsed: list[float] = []
    stages: dict[str, list[float]] = {}
    errors: dict[str, int] = {}
    for _ in range(repetitions):
        measurement = run()
        metrics = json.loads(canonical_bytes(measurement.metrics))
        elapsed.append(metrics["elapsed_seconds"])
        for name, duration in metrics["stage_seconds"].items():
            stages.setdefault(name, []).append(duration)
        code = measurement.error.value if measurement.error else "success"
        errors[code] = errors.get(code, 0) + 1
    peak = None
    if python_memory:
        tracemalloc.start()
        run()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    try:
        import resource

        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss_bytes: int | None = int(rss * (1 if sys.platform == "darwin" else 1024))
    except ImportError:
        rss_bytes = None
    stream = io.StringIO()
    if profile_enabled:
        profile = cProfile.Profile()
        profile.runcall(run)
        pstats.Stats(profile, stream=stream).strip_dirs().sort_stats("cumulative").print_stats(20)
    fields = (
        [source]
        if isinstance(source, FieldInput)
        else [item.source for item in source.fields if item.source is not None]
    )
    return {
        "name": case.name,
        "cohort": case.cohort,
        "unit": "field" if isinstance(source, FieldInput) else "record",
        "input_sha256": hashlib.sha256(canonical_bytes(source)).hexdigest(),
        "input_codepoints": sum(len(f.value) for f in fields),
        "fields": len(fields),
        "html_fraction": sum(f.source_format is SourceFormat.HTML_FRAGMENT for f in fields)
        / len(fields),
        "cold_seconds": cold,
        "latency_seconds": distribution(elapsed),
        "throughput_units_per_second": repetitions / sum(elapsed),
        "successful_units_per_second": errors.get("success", 0) / sum(elapsed),
        "stage_seconds": {name: distribution(values) for name, values in stages.items()},
        "outcomes": errors,
        "python_peak_bytes_separate_run": peak,
        "process_peak_rss_bytes": rss_bytes,
        "metrics_example": json.loads(canonical_bytes(first.metrics)),
        "profile_separate_run": stream.getvalue() if profile_enabled else None,
    }


def environment() -> dict[str, Any]:
    cpu = platform.processor()
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        cpu = next(
            (
                line.split(":", 1)[1].strip()
                for line in cpuinfo.read_text().splitlines()
                if line.startswith("model name")
            ),
            cpu,
        )
    memory: dict[str, int] = {}
    if Path("/proc/meminfo").exists():
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            if key in {"MemTotal", "MemAvailable", "SwapTotal"}:
                memory[key + "_bytes"] = int(value.split()[0]) * 1024
    cgroup = {
        name: path.read_text().strip()
        for name in ("memory.max", "cpu.max")
        if (path := Path("/sys/fs/cgroup") / name).exists()
    }
    return {
        "os": platform.platform(),
        "machine": platform.machine(),
        "cpu": cpu,
        "logical_cpus": os.cpu_count(),
        "affinity_cpus": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
        "memory_snapshot": memory,
        "visible_cgroup_limits": cgroup,
        "python": sys.version,
        "manifest": json.loads(canonical_bytes(create_manifest())),
        "lock_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
    }


def compare(current: dict[str, Any], baseline: dict[str, Any], percent: float) -> list[str]:
    failures = []
    for key in ("os", "machine", "cpu", "logical_cpus", "python", "lock_sha256"):
        if current["environment"][key] != baseline["environment"][key]:
            failures.append(f"incomparable environment: {key}")
    if current["protocol"] != baseline["protocol"]:
        failures.append("incomparable measurement protocol")
    previous = {case["name"]: case for case in baseline["cases"]}
    if set(previous) != {case["name"] for case in current["cases"]}:
        failures.append("incomparable workload inventory")
    for case in current["cases"]:
        old = previous.get(case["name"])
        if old is None or "latency_seconds" not in case or "latency_seconds" not in old:
            failures.append(f"incomplete measurement: {case['name']}")
            continue
        if case["input_sha256"] != old["input_sha256"] or case["outcomes"] != old["outcomes"]:
            failures.append(f"changed input/outcomes: {case['name']}")
        for metric in ("p50", "p95", "p99"):
            if case["latency_seconds"][metric] > old["latency_seconds"][metric] * (
                1 + percent / 100
            ):
                failures.append(f"latency regression: {case['name']} {metric}")
        old_rss, new_rss = old.get("process_peak_rss_bytes"), case.get("process_peak_rss_bytes")
        if old_rss and new_rss and new_rss > old_rss * (1 + percent / 100):
            failures.append(f"RSS regression: {case['name']}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/normietext-load.json"))
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--worker-timeout", type=float, default=120)
    parser.add_argument("--worker-memory-mib", type=int)
    parser.add_argument("--python-memory", action="store_true")
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--case", action="append")
    parser.add_argument("--worker")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--max-regression-percent", type=float)
    args = parser.parse_args()
    if (
        args.warmup < 0
        or args.repetitions < 1
        or args.worker_timeout <= 0
        or not math.isfinite(args.worker_timeout)
    ):
        parser.error("positive repetitions/timeout and nonnegative warmup required")
    if args.baseline and (
        args.max_regression_percent is None
        or args.max_regression_percent < 0
        or not math.isfinite(args.max_regression_percent)
    ):
        parser.error("comparison requires an explicit nonnegative regression threshold")
    if args.worker_memory_mib is not None and (
        args.worker_memory_mib <= 0 or sys.platform != "linux"
    ):
        parser.error("memory containment requires Linux and a positive MiB limit")
    cases = workloads()
    names = {case.name for case in cases}
    if set(args.case or ()) - names or (args.worker and args.worker not in names):
        parser.error("unknown workload")
    if args.worker:
        if args.worker_memory_mib is not None:
            import resource

            ceiling = args.worker_memory_mib * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))
        case = next(c for c in cases if c.name == args.worker)
        print(
            json.dumps(
                run_case(
                    case,
                    args.warmup,
                    args.repetitions,
                    python_memory=args.python_memory,
                    profile_enabled=args.profile,
                ),
                ensure_ascii=False,
            )
        )
        return
    results = []
    for case in cases:
        if args.case and case.name not in args.case:
            continue
        command = [
            sys.executable,
            "-m",
            "benchmarks.load",
            "--worker",
            case.name,
            "--warmup",
            str(args.warmup),
            "--repetitions",
            str(args.repetitions),
        ]
        if args.python_memory:
            command.append("--python-memory")
        if args.profile:
            command.append("--profile")
        if args.worker_memory_mib is not None:
            command.extend(("--worker-memory-mib", str(args.worker_memory_mib)))
        try:
            worker = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=args.worker_timeout,
                check=False,
            )
            result = (
                json.loads(worker.stdout)
                if worker.returncode == 0
                else {
                    "name": case.name,
                    "cohort": case.cohort,
                    "worker_error": "failed",
                    "returncode": worker.returncode,
                }
            )
        except subprocess.TimeoutExpired:
            result = {"name": case.name, "cohort": case.cohort, "worker_error": "timeout"}
        results.append(result)
        print(f"Measured {case.name}", file=sys.stderr, flush=True)
    report = {
        "schema_version": "1.0.0",
        "environment": environment(),
        "protocol": {
            "warmup": args.warmup,
            "repetitions": args.repetitions,
            "worker_timeout_seconds": args.worker_timeout,
            "worker_memory_mib": args.worker_memory_mib,
            "python_memory": args.python_memory,
            "profile": args.profile,
            "percentiles": "nearest rank",
            "memory_and_profile": "separate runs",
        },
        "limitations": [
            "Synthetic public samples, not production traffic",
            "Small sample tail percentiles are descriptive, not a production SLO",
            "RSS is lifetime process high-water including warmup and memory run",
            "Worker timeout is for the entire benchmark, not a per-record SLO",
        ],
        "cases": results,
    }
    failures = (
        compare(report, json.loads(args.baseline.read_bytes()), args.max_regression_percent)
        if args.baseline
        else []
    )
    report["comparison_failures"] = failures
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if failures or any("worker_error" in case for case in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
