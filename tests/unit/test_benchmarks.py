"""Benchmark summaries and explicit regression gates; no wall-time assertions."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from benchmarks import batch, load
from benchmarks.load import compare, distribution, workloads


def test_percentiles_keep_small_sample_tail_limit_visible():
    result = distribution([4.0, 1.0, 3.0, 2.0])
    assert result["p50"] == 2 and result["p95"] == result["p99"] == 4
    assert result["samples"] == 4 and result["min"] == 1 and result["max"] == 4


def test_regression_gate_rejects_changed_inputs_environment_and_missing_measurements():
    report = {
        "environment": dict.fromkeys(
            ["os", "machine", "cpu", "logical_cpus", "python", "lock_sha256"], "fixed"
        ),
        "protocol": {"warmup": 2},
        "cases": [
            {
                "name": "case",
                "input_sha256": "abc",
                "outcomes": {"success": 5},
                "latency_seconds": {"p50": 1, "p95": 2, "p99": 3},
                "process_peak_rss_bytes": 100,
            }
        ],
    }
    assert compare(report, deepcopy(report), 20) == []
    changed = deepcopy(report)
    changed["cases"][0]["latency_seconds"]["p99"] = 4
    assert compare(changed, report, 20) == ["latency regression: case p99"]
    changed["environment"]["cpu"] = "other"
    changed["cases"][0]["input_sha256"] = "different"
    assert "incomparable environment: cpu" in compare(changed, report, 20)
    assert "changed input/outcomes: case" in compare(changed, report, 20)
    changed["cases"][0] = {"name": "case", "worker_error": "timeout"}
    assert "incomplete measurement: case" in compare(changed, report, 20)


def test_load_inventory_separates_cohorts_and_contains_both_api_units():
    cases = workloads()
    assert len({case.name for case in cases}) == len(cases)
    assert {case.cohort for case in cases} == {"synthetic_representative", "adversarial"}
    assert {"six_fields", "integral", "hints_2000", "max_plain", "html_nodes"} <= {
        case.name for case in cases
    }


def test_windows_benchmarks_preserve_results_without_importing_resource(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def checked_import(name, *args, **kwargs):
        if name == "resource":
            pytest.fail("Windows benchmarks must not import the Unix resource module")
        return original_import(name, *args, **kwargs)

    case = next(case for case in workloads() if case.name == "compact")
    # Replace only the harness references, not Python's global platform state.
    monkeypatch.setattr(load, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(batch, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(builtins, "__import__", checked_import)
    field = load.run_case(case, warmup=0, repetitions=1)
    record = batch.process(2)
    assert field["process_peak_rss_bytes"] is None
    assert field["outcomes"] == {"success": 1}
    assert record["process_peak_rss_bytes"] is None
    assert record["errors"] == []


@pytest.mark.parametrize("platform", ["win32", "darwin"])
def test_non_linux_worker_rejects_memory_containment(monkeypatch, capsys, platform):
    monkeypatch.setattr(load, "sys", SimpleNamespace(platform=platform))
    monkeypatch.setattr("sys.argv", ["load", "--worker", "compact", "--worker-memory-mib", "256"])
    with pytest.raises(SystemExit) as error:
        load.main()
    assert error.value.code == 2
    assert "memory containment requires Linux" in capsys.readouterr().err
