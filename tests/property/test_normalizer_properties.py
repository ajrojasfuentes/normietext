"""Composed pipeline invariants, including Unicode adjacency and typed reentry."""

from hypothesis import given, settings
from hypothesis import strategies as st

from normietext import FieldInput, JobField, JobTextNormalizer
from normietext.serialization import canonical_bytes
from normietext.validation import validate_text

NORMALIZER = JobTextNormalizer()


@given(
    st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=100),
    st.sampled_from(list(JobField)),
)
@settings(max_examples=150, deadline=None)
def test_output_invariants_and_typed_reentry(raw, field):
    result = NORMALIZER.normalize_field(FieldInput(field, raw))
    validate_text(result.text, compact=field.value in NORMALIZER.policy.output.compact_fields)
    assert result.source.raw == raw
    assert NORMALIZER.canonicalize(result) is result
    assert canonical_bytes(NORMALIZER.normalize_field(FieldInput(field, raw))) == canonical_bytes(
        result
    )
    assert all(b.span.within(result.text) for b in result.blocks)
    for a in result.annotations:
        assert result.text[a.span.start : a.span.end] == a.rendered_token


@given(
    st.lists(
        st.sampled_from(
            [
                "a",
                "\u0301",
                "\u200b",
                "🚀",
                "🔥",
                "🇨🇷",
                "✅",
                "©️",
                "1️⃣",
                "🛸️\u0301",
                " ",
                "\n",
                "\t",
                "👉️",
                "C++",
                "\uff0f",
            ]
        ),
        max_size=25,
    )
)
@settings(max_examples=150, deadline=None)
def test_lexical_adjacencies(parts):
    raw = "".join(parts)
    result = NORMALIZER.normalize_field(FieldInput(JobField.JOB_DESCRIPTION, raw))
    assert NORMALIZER.canonicalize(result) is result
