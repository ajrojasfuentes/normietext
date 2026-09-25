from dataclasses import FrozenInstanceError

import pytest
from hypothesis import given
from hypothesis import strategies as st

from normietext.errors import InputValidationError
from normietext.models import FieldInput, JobField, Span, freeze_json
from normietext.policy import ResourceLimits


@given(st.text(alphabet=st.characters(blacklist_categories=("Cs",))))
def test_valid_unicode_is_preserved_by_input_contract(raw: str) -> None:
    source = FieldInput(JobField.JOB_DESCRIPTION, raw)
    assert source.value == raw
    with pytest.raises(FrozenInstanceError):
        source.value = "changed"


@given(st.integers(min_value=0xD800, max_value=0xDFFF))
def test_every_isolated_surrogate_is_rejected(codepoint: int) -> None:
    with pytest.raises(InputValidationError):
        FieldInput(JobField.JOB_TITLE, chr(codepoint))


@given(st.integers(min_value=0, max_value=262144))
def test_output_budget_covers_hint_only_expansion(length: int) -> None:
    assert ResourceLimits().output_limit(length) >= max(0, length * 26 - 1)


@given(st.integers(min_value=0, max_value=1000), st.integers(min_value=0, max_value=1000))
def test_spans_use_nonnegative_half_open_positions(start: int, width: int) -> None:
    span = Span(start, start + width)
    assert span.within("x" * (start + width))


@given(
    st.lists(
        st.one_of(
            st.none(),
            st.booleans(),
            st.integers(),
            st.text(alphabet=st.characters(blacklist_categories=("Cs",))),
        )
    )
)
def test_json_arrays_are_detached(values: list[object]) -> None:
    frozen = freeze_json(values)
    before = tuple(values)
    values.append("mutated")
    assert frozen == before
