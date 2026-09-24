"""Check the installed distribution contract, not normalization behavior."""

from importlib.metadata import metadata
from importlib.resources import files

import normietext


def test_distribution_metadata_and_typing_marker() -> None:
    distribution = metadata("normietext")
    assert distribution["Name"] == "normietext"
    assert distribution["Requires-Python"].replace(" ", "") == ">=3.14,<3.15"
    assert files(normietext).joinpath("py.typed").is_file()
