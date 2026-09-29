import os
import subprocess
import sys


def test_f4_replay_across_processes_without_network():
    script = r"""
import socket
socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network"))
socket.create_connection = socket.socket.connect
from normietext import FieldInput, JobField, SourceFormat
from normietext.adapters import convert_source
from normietext.stages.encoding import repair_document
from normietext.stages.lexing import lex_document
from normietext.serialization import canonical_bytes
raw = '<p>JosÃ© 🇨🇷</p><pre>  C++ 🚀</pre><dl><dt>Type</dt><dd>don\x92t</dd></dl>'
source = FieldInput(JobField.JOB_DESCRIPTION, raw, SourceFormat.HTML_FRAGMENT)
result = lex_document(repair_document(convert_source(source)))
assert result.document.text == "José 🇨🇷\n  C++ 🚀\nType\ndon\u2019t"
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
