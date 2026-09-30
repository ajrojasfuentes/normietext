"""Evaluation replay, including order independence and offline execution."""

import os
import subprocess
import sys

from evaluation.evidence import collect
from normietext import FieldInput, JobField, JobTextNormalizer, SourceFormat


def test_evidence_metamorphic_formats_and_line_endings():
    normalizer = JobTextNormalizer()
    variants = [
        ("Python & SQL\nUSD 0.004/request", SourceFormat.PLAIN_TEXT),
        ("Python & SQL\r\nUSD 0.004/request", SourceFormat.PLAIN_TEXT),
        ("Python &amp; SQL\nUSD 0.004/request", SourceFormat.HTML_ESCAPED_TEXT),
        ("<p>Py<b>th</b>on &amp; SQL</p><p>USD 0.004/request</p>", SourceFormat.HTML_FRAGMENT),
    ]
    evidence = []
    for raw, fmt in variants:
        result = normalizer.normalize_field(FieldInput(JobField.JOB_DESCRIPTION, raw, fmt))
        evidence.append(
            [(c.kind, c.value, c.amounts, c.currency, c.period) for c in collect(result)]
        )
    assert all(item == evidence[0] for item in evidence)


def test_evaluation_replay_across_hash_seeds_and_order():
    script = """
import socket
socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network"))
socket.create_connection = socket.socket.connect
from evaluation.quality import evaluate, FIXTURES
from evaluation.evidence import collect, evidence_bytes
from normietext import FieldInput, JobField, JobTextNormalizer, SourceFormat
import json, sys
from hashlib import sha256
cases = json.loads((FIXTURES/'quality/cases.json').read_bytes())['cases']
n = JobTextNormalizer()
def run(items):
    return {c['id']: evidence_bytes(collect(n.normalize_field(FieldInput(
        JobField(c['field']), c['raw'], SourceFormat(c['source_format']))))) for c in items}
assert run(cases) == run(reversed(cases))
report = evaluate()
assert report['passed']
sys.stdout.buffer.write(sha256(evidence_bytes(report)).digest())
"""
    outputs = [
        subprocess.check_output(
            [sys.executable, "-c", script], env=dict(os.environ, PYTHONHASHSEED=seed)
        )
        for seed in ("0", "1", "42", "random")
    ]
    assert all(output == outputs[0] for output in outputs)
