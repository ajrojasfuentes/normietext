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


@given(
    st.integers(min_value=0, max_value=0x120000),
    st.integers(min_value=0, max_value=4500),
    st.booleans(),
)
def test_numeric_entity_padding_preserves_html5_value_without_large_integer_conversion(
    value, zeros, hexadecimal
):
    digits = format(value, "x") if hexadecimal else str(value)
    prefix = "&#x" if hexadecimal else "&#"
    reference = prefix + "0" * zeros + digits + ";"
    expected = html.unescape(prefix + digits + ";")
    document = convert_source(
        FieldInput(JobField.JOB_DESCRIPTION, reference, SourceFormat.HTML_ESCAPED_TEXT)
    )
    # Adaptation tokenizes any decoded separators after one-layer decoding.
    expected = expected.replace("\r\n", "\n")
    for separator in "\r\x85\u2028\u2029\v\f":
        expected = expected.replace(separator, "\n")
    assert document.text == expected
