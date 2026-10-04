"""Benchmark summaries and explicit regression gates; no wall-time assertions."""

from copy import deepcopy

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
