"""Stable complete records across hash seeds and input processing order, offline."""

import os
import subprocess
import sys


def test_complete_pipeline_replay_without_network():
    script = r"""
import socket
socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network"))
socket.create_connection = socket.socket.connect
from normietext import *
from normietext.serialization import canonical_bytes
from concurrent.futures import ThreadPoolExecutor
n = JobTextNormalizer()
raws = ['JosÃ© 🇨🇷','• A\n  continued\n• B','C++🚀Python',
        '<dl><dt>Type</dt><dd>Full-time</dd></dl>','Not Specified','🇲🇽']
sources = [FieldInput(f,raw,SourceFormat.HTML_FRAGMENT
           if raw.startswith('<dl>') else SourceFormat.PLAIN_TEXT)
           for f,raw in zip(JobField,raws)]
record = JobInputRecord(tuple(InputField(s.field,ExtractionStatus.PRESENT,s) for s in sources))
result = n.normalize_record(record)
with ThreadPoolExecutor(max_workers=3) as pool:
    reversed_results = list(pool.map(n.normalize_field,reversed(sources)))
assert tuple(reversed(reversed_results)) == tuple(f.result for f in result.fields)
assert all(n.canonicalize(f.result) is f.result for f in result.fields)
import sys
sys.stdout.buffer.write(canonical_bytes(result))
"""
    outputs = [
        subprocess.check_output(
            [sys.executable, "-c", script], env=dict(os.environ, PYTHONHASHSEED=seed)
        )
        for seed in ("0", "1", "42", "random")
    ]
    assert all(output == outputs[0] for output in outputs)
