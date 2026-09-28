import os
import subprocess
import sys


def test_html_structure_and_associations_replay_across_hash_seeds():
    script = r"""
import socket
socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network"))
from normietext import FieldInput, JobField, SourceFormat
from normietext.adapters import convert_source
from normietext.serialization import canonical_bytes
raw = '<ol reversed><li>Python<br>SQL</li><li>R</li></ol><dl><dt>Type</dt><dd>FT</dd></dl><a href="https://example.invalid">Apply</a>'
result = convert_source(FieldInput(JobField.JOB_DESCRIPTION, raw, SourceFormat.HTML_FRAGMENT))
import sys
sys.stdout.buffer.write(canonical_bytes(result))
"""
    outputs = [
        subprocess.check_output(
            [sys.executable, "-c", script], env=dict(os.environ, PYTHONHASHSEED=seed)
        )
        for seed in ("0", "1", "42", "random")
    ]
    assert all(value == outputs[0] for value in outputs)
