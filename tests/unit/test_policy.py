from dataclasses import FrozenInstanceError

import pytest

from normietext.errors import ModelValidationError, PolicyValidationError
from normietext.models import JobField
from normietext.policy import NormalizationPolicy, ResourceLimits


def test_policy_rejects_unknown_or_unimplemented_behavior() -> None:
    for data in (
        {"unknown": 1},
        {"encoding": {"typo": True}},
        {"input": {"auto_detect_html": True}},
        {"policy_id": "other"},
        {"limits": {"job_title": True}},
        {"limits": {"max_expansion_factor": 16}},
    ):
        with pytest.raises(PolicyValidationError):
            NormalizationPolicy.from_dict(data)


def test_limits_are_independent_and_policy_cannot_mutate() -> None:
    policy = NormalizationPolicy()
    limits = policy.limits
    assert sum(limits.for_field(f) for f in JobField) == 319488 < limits.record
    assert limits.output_limit(2000) >= 2000 * 26 - 1
    assert limits.output_limit(0) == 1024
    changed = NormalizationPolicy.from_dict({"limits": {"record": 100}})
    assert changed.limits.record == 100
    assert policy.limits.record == 327680
    with pytest.raises(FrozenInstanceError):
        policy.limits.record = 0
    with pytest.raises(ModelValidationError):
        ResourceLimits(html_nodes=0)
