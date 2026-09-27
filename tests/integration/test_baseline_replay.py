import os
import subprocess
import sys


def test_replay_bytes_across_hash_seeds_without_network():
    script = r"""
import socket
socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network"))
socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network"))
from normietext import FieldInput, JobField, SourceEvidence, NormalizedField
from normietext.manifest import create_manifest
from normietext.provenance import TrackedText
from normietext.rendering import render_baseline
from normietext.serialization import canonical_bytes
from normietext.validation import validate_canonical
source = SourceEvidence.from_input(FieldInput(JobField.JOB_DESCRIPTION, "  a\u0301\r\n x  x "))
tracked = render_baseline(TrackedText.from_source(source), compact=False)
manifest = create_manifest()
result = NormalizedField(source, tracked.text, manifest, edits=tracked.edits)
assert validate_canonical(result, expected_manifest=manifest) is result
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
    assert b'"text":"\xc3\xa1\\nx x"' in outputs[0]
