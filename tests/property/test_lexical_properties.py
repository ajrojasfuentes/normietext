from hypothesis import given, settings
from hypothesis import strategies as st

from normietext import FieldInput, JobField
from normietext.adapters import convert_source
from normietext.serialization import canonical_bytes
from normietext.stages.encoding import repair_document
from normietext.stages.lexing import lex_document


@given(st.text(alphabet="abc áéÃ©\u0301\t\r\n\x85\x01\u200b🚀⚠🇨🇷©1#*`", max_size=100))
@settings(max_examples=60, deadline=None)
def test_lexical_partition_preserves_text_source_and_typed_reentry(raw):
    converted = convert_source(FieldInput(JobField.JOB_DESCRIPTION, raw))
    repaired = repair_document(converted)
    result = lex_document(repaired)
    assert "".join(repaired.text[t.span.start : t.span.end] for t in result.tokens) == repaired.text
    assert result.document.source.raw == raw
    assert repair_document(repaired) is repaired
    assert lex_document(result) is result
    assert canonical_bytes(result) == canonical_bytes(lex_document(repair_document(converted)))
    assert all(t.origin.span is None or t.origin.span.end <= len(raw) for t in result.tokens)
