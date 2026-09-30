"""Unicode spans and evidence survive composed punctuation/format transforms."""

from hypothesis import given, settings
from hypothesis import strategies as st

from evaluation.evidence import collect
from evaluation.quality import span_errors
from normietext import FieldInput, JobField, JobTextNormalizer, SourceFormat

N = JobTextNormalizer()


@given(
    st.lists(
        st.sampled_from(
            ["𐐀", "á", "🇨🇷", "Python", "C++", "USD 0.004/request", "🚀", "Node.js", "a\u200b́"]
        ),
        min_size=1,
        max_size=12,
    )
)
@settings(max_examples=70, deadline=None)
def test_all_spans_under_unicode_composition(parts):
    raw = " ".join(parts)
    for fmt, value in [
        (SourceFormat.PLAIN_TEXT, raw),
        (SourceFormat.HTML_FRAGMENT, "<ul><li>" + raw + "</li><li></li></ul>"),
    ]:
        result = N.normalize_field(FieldInput(JobField.JOB_DESCRIPTION, value, fmt))
        assert not span_errors(result)
        for candidate in collect(result):
            assert result.text[candidate.span.start : candidate.span.end] == candidate.text
        assert N.canonicalize(result) is result
