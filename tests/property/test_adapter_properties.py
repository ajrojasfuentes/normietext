import html

from hypothesis import given
from hypothesis import strategies as st

from normietext import FieldInput, JobField, SourceFormat
from normietext.adapters import convert_source, tracked_document


@given(st.text(alphabet='abc áé<>;&"\t\n\r\x85💰\u200d\ufe0f', max_size=80))
def test_declared_escaped_text_decodes_one_layer_and_preserves_raw(text):
    escaped = html.escape(text)
    document = convert_source(
        FieldInput(JobField.JOB_DESCRIPTION, escaped, SourceFormat.HTML_ESCAPED_TEXT)
    )
    expected = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x85", "\n")
    assert document.text == expected
    assert document.source.raw == escaped
    assert tracked_document(document).alignment.output_length == len(expected)


@given(
    st.lists(
        st.text(alphabet="ab áé\t💰\u200d\ufe0f", min_size=1, max_size=15), min_size=1, max_size=8
    )
)
def test_inline_markup_never_inserts_spaces_or_discards_lexical_components(parts):
    raw = "<p>" + "".join("<b>" + html.escape(text) + "</b>" for text in parts) + "</p>"
    document = convert_source(FieldInput(JobField.JOB_DESCRIPTION, raw, SourceFormat.HTML_FRAGMENT))
    assert document.text == "".join(parts)
    assert document.source.raw == raw
    assert all(block.span.end <= len(document.text) for block in document.blocks)
