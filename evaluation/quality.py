"""Reproducible F6 corpus, evidence and list-decision report (no timing claims)."""

import argparse
import hashlib
import json
import re
from bisect import bisect_right
from collections import Counter, defaultdict
from decimal import Decimal
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path
from typing import Any

from evaluation.ablations import RULES, without_rule
from evaluation.evidence import collect, evidence_bytes, wire
from normietext import FieldInput, JobField, JobTextNormalizer, SourceFormat
from normietext.adapters import convert_source
from normietext.manifest import create_manifest
from normietext.stages.encoding import repair_document
from normietext.stages.lexing import lex_document
from normietext.stages.structure import resolve_structure

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_corpus() -> None:
    catalog = json.loads((FIXTURES / "catalog.json").read_bytes())
    for name, expected in catalog["files"].items():
        if digest(FIXTURES / name) != expected:
            raise ValueError("Corpus integrity mismatch: " + name)


def percentage(numerator: int, denominator: int) -> str | None:
    return (
        str((Decimal(numerator) * 100 / denominator).quantize(Decimal("0.001")))
        if denominator
        else None
    )


def metrics(counts: Counter[str]) -> dict[str, Any]:
    total = sum(counts[k] for k in ("tp", "fp", "tn", "fn", "abstained"))
    return dict(
        {key: counts[key] for key in ("tp", "fp", "tn", "fn", "abstained")},
        labeled=total,
        predicted=counts["tp"] + counts["fp"],
        precision_pct=percentage(counts["tp"], counts["tp"] + counts["fp"]),
        recall_pct=percentage(counts["tp"], counts["tp"] + counts["fn"]),
        coverage_pct=percentage(counts["tp"] + counts["fp"], total),
        abstention_pct=percentage(counts["abstained"], total),
    )


def span_errors(result: Any) -> list[str]:
    errors = []
    by_id = {b.id: b for b in result.blocks}
    for block in result.blocks:
        if not block.span.within(result.text):
            errors.append("block_outside_text")
        if block.parent_id is not None:
            parent = by_id[block.parent_id]
            if not parent.span.start <= block.span.start <= block.span.end <= parent.span.end:
                errors.append("child_outside_parent")
    for annotation in result.annotations:
        if (
            annotation.span is not None
            and annotation.rendered_token is not None
            and result.text[annotation.span.start : annotation.span.end]
            != annotation.rendered_token
        ):
            errors.append("annotation_span")
    for candidate in collect(result):
        if result.text[candidate.span.start : candidate.span.end] != candidate.text:
            errors.append("candidate_span")
        if (
            candidate.kind != "region"
            and candidate.origin.span is not None
            and candidate.origin.precision.value == "exact"
        ):
            raw = result.source.raw
            if (
                raw is None
                or raw[candidate.origin.span.start : candidate.origin.span.end] != candidate.text
            ):
                errors.append("invented_exact_origin")
    return errors


def evaluate(*, ablate: bool = True) -> dict[str, Any]:
    verify_corpus()
    normalizer = JobTextNormalizer()
    cases = json.loads((FIXTURES / "quality/cases.json").read_bytes())["cases"]
    failures: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()
    segments: dict[str, Counter[str]] = defaultdict(Counter)
    ablations: dict[str, Counter[str]] = {rule: Counter() for rule in RULES}
    ablation_segments: dict[str, Counter[str]] = defaultdict(Counter)
    observations = []
    for left, right in combinations(cases, 2):
        if left["split"] == right["split"]:
            continue
        a, b = (re.sub(r"\s+", " ", c["raw"].casefold()).strip() for c in (left, right))
        if SequenceMatcher(None, a, b, autojunk=False).ratio() >= 0.85:
            raise ValueError("Near duplicate split leakage: " + left["id"] + "/" + right["id"])
    families: dict[str, str] = {}
    exact_texts: dict[str, str] = {}
    evidence_total = losses_total = 0
    for case in cases:
        family, split = case["family"], case["split"]
        if families.setdefault(family, split) != split:
            raise ValueError("Family split leakage: " + family)
        normalized_raw = " ".join(case["raw"].casefold().split())
        if exact_texts.setdefault(normalized_raw, split) != split:
            raise ValueError("Duplicate split leakage: " + case["id"])
        source = FieldInput(
            JobField(case["field"]), case["raw"], SourceFormat(case["source_format"])
        )
        lexed = lex_document(repair_document(convert_source(source)))
        result = normalizer.canonicalize(lexed)
        reasons = span_errors(result)
        if result.text != case["expected"]:
            reasons.append("golden_text")
        if result.source.raw != source.value or normalizer.canonicalize(result) is not result:
            reasons.append("source_or_reentry")
        missing = [fragment for fragment in case["required"] if fragment not in result.text]
        if missing:
            reasons.append("required_evidence")
        lost = [
            fragment
            for fragment in case["authorized_losses"]
            if fragment in source.value and fragment not in result.text
        ]
        if len(lost) != len(case["authorized_losses"]):
            reasons.append("authorized_loss_expectation")
        evidence_total += len(case["required"])
        losses_total += len(lost)
        candidates = collect(result)
        actual_tech = [c.value for c in candidates if c.kind == "technology"]
        if actual_tech != case["technologies"]:
            reasons.append("technology_consumer")
        if [c.value for c in candidates if c.kind == "region"] != case["regions"]:
            reasons.append("region_consumer")
        if not set(case["roles"]) <= {c.context.role for c in candidates}:
            reasons.append("context_consumer")
        starts = [0] + [i + 1 for i, char in enumerate(lexed.document.text) if char == "\n"]
        lines = lexed.document.text.split("\n")
        recognized = resolve_structure(lexed, normalizer.policy)
        final_ids = {b.id for b in result.blocks if b.kind.value == "list_item"}
        inferred = {
            bisect_right(starts, b.span.start) - 1
            for b in recognized.blocks
            if b.id in final_ids and b.origin_tag is None
        }
        explicit = {
            bisect_right(starts, b.span.start) - 1
            for b in recognized.blocks
            if b.id in final_ids and b.origin_tag is not None
        }
        labeled = {label["line"] for label in case["labels"]}
        if inferred - labeled:
            reasons.append("unlabeled_prediction")
        counts: Counter[str] = Counter()
        for label in case["labels"]:
            index, expected = label["line"], label["label"]
            if index >= len(lines) or not lines[index].strip():
                reasons.append("invalid_authored_label")
                continue
            if expected == "explicit":
                if index not in explicit:
                    reasons.append("missing_dom_item")
                continue
            predicted = index in inferred
            category = (
                ("tp" if predicted else "fn")
                if expected == "item"
                else ("fp" if predicted else "abstained" if expected == "abstain" else "tn")
            )
            counts[category] += 1
        totals.update(counts)
        for key in ("split", "language", "source_format", "field"):
            segments[key + ":" + case[key]].update(counts)
        if counts["fp"] or counts["fn"]:
            reasons.append("list_decision")
        if reasons:
            failures.append(
                dict(
                    id=case["id"], reasons=sorted(set(reasons)), missing=missing, actual=result.text
                )
            )
        observations.append(dict(id=case["id"], counts=dict(counts), candidates=wire(candidates)))
        if ablate:
            applied = {edit.rule_id for edit in result.edits}
            for rule in RULES:
                if rule not in applied:
                    continue
                view = without_rule(lexed, rule, normalizer.policy)
                before = collect(view)
                comparison: Counter[str] = Counter()
                comparison["cases"] += 1
                comparison["changed_text"] += view.text != result.text
                comparison["required_present_with"] += sum(
                    f in result.text for f in case["required"]
                )
                comparison["required_present_without"] += sum(
                    f in view.text for f in case["required"]
                )
                comparison["authorized_absent_with"] += sum(
                    f not in result.text for f in case["authorized_losses"]
                )
                comparison["authorized_absent_without"] += sum(
                    f not in view.text for f in case["authorized_losses"]
                )
                comparison["technology_with"] += len(actual_tech)
                comparison["technology_without"] += sum(c.kind == "technology" for c in before)
                comparison["region_with"] += sum(c.kind == "region" for c in candidates)
                comparison["region_without"] += sum(c.kind == "region" for c in before)
                comparison["list_items_with"] += sum(
                    b.kind.value == "list_item" for b in result.blocks
                )
                comparison["list_items_without"] += sum(
                    b.kind.value == "list_item" for b in view.blocks
                )
                ablations[rule].update(comparison)
                for key in ("split", "language", "source_format", "field"):
                    ablation_segments[rule + "|" + key + ":" + case[key]].update(comparison)
    mandatory = []
    regression = json.loads((FIXTURES / "regression/cases.json").read_bytes())["cases"]
    for case in regression:
        if case["input_type"] != "text" or "text" not in case["expected"]:
            continue
        result = normalizer.normalize_field(
            FieldInput(JobField(case["field"]), case["raw"], SourceFormat(case["source_format"]))
        )
        expected = case["expected"]["text"]
        # Mandatory negative regression lines must not acquire inferred items.
        if result.text != expected:
            failures.append({"id": case["id"], "reasons": ["mandatory_golden"]})
        if not re.search(r"(?m)^(?:- |\d+\. )", expected):
            fp = sum(b.kind.value == "list_item" and b.origin_tag is None for b in result.blocks)
            mandatory.append({"id": case["id"], "false_positives": fp})
            if fp:
                failures.append({"id": case["id"], "reasons": ["mandatory_false_positive"]})
    inventory = json.loads((FIXTURES / "quality/integral_evidence.json").read_bytes())
    integral_root = FIXTURES / "integral/complex_multilingual_ai_role_001"
    integral = {
        field: normalizer.normalize_field(
            FieldInput(
                JobField(field), (integral_root / (field + ".raw.txt")).read_bytes().decode()
            )
        )
        for field in ("job_title", "job_description")
    }
    integral_missing = []
    for requirement in inventory["requirements"]:
        for fragment in requirement["fragments"]:
            if fragment not in integral[requirement["field"]].text:
                integral_missing.append({"id": requirement["id"], "fragment": fragment})
    combined = "\n".join(result.text for result in integral.values())
    integral_losses = [
        fragment for fragment in inventory["authorized_losses"] if fragment not in combined
    ]
    if integral_missing or len(integral_losses) != len(inventory["authorized_losses"]):
        failures.append({"id": "integral_evidence", "missing": integral_missing})
    runtime = create_manifest()
    return dict(
        schema_version="1.0.0",
        corpus="synthetic_public_not_blind",
        split_audit="family + casefold whitespace exact + SequenceMatcher >= 0.85",
        case_count=len(cases),
        corpus_sha256=digest(FIXTURES / "catalog.json"),
        lock_sha256=digest(ROOT / "uv.lock"),
        evaluator_sha256=hashlib.sha256(
            b"".join(p.read_bytes() for p in sorted((ROOT / "evaluation").glob("*.py")))
        ).hexdigest(),
        manifest=wire(runtime),
        list_metrics=metrics(totals),
        segments={k: metrics(v) for k, v in sorted(segments.items())},
        required_fragments=evidence_total,
        authorized_losses=losses_total,
        integral=dict(
            requirement_groups=len(inventory["requirements"]),
            fragments=sum(len(r["fragments"]) for r in inventory["requirements"]),
            missing=integral_missing,
            authorized_losses=len(integral_losses),
        ),
        ablations={rule: dict(counts) for rule, counts in ablations.items()},
        mandatory_negatives=mandatory,
        ablation_segments={key: dict(value) for key, value in sorted(ablation_segments.items())},
        failures=failures,
        observations=observations,
        passed=not failures
        and totals["tp"] > 0
        and Decimal(totals["tp"]) / (totals["tp"] + totals["fp"]) >= Decimal("0.995"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate()
    data = evidence_bytes(report) + b"\n"
    if args.output:
        args.output.write_bytes(data)
    else:
        print(data.decode(), end="")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
