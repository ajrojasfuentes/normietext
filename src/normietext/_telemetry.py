"""Opt-in call-local measurements, never part of canonical serialization."""

from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from time import perf_counter


@dataclass
class StageCapture:
    timings: dict[str, float] = field(default_factory=dict)
    capture_trace: bool = False
    snapshots: list[tuple[str, object]] = field(default_factory=list)


capture: ContextVar[StageCapture | None] = ContextVar("normietext_measurement", default=None)


def measured[T, **P](stage: str, function: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    active = capture.get()
    if active is None:
        return function(*args, **kwargs)
    start = perf_counter()
    try:
        result = function(*args, **kwargs)
        if active.capture_trace:
            active.snapshots.append((stage, result))
        return result
    finally:
        active.timings[stage] = active.timings.get(stage, 0.0) + perf_counter() - start
