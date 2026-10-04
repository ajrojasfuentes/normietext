import hashlib

import pytest

from scripts.release_assets import checksums


def test_checksums_cover_exact_verified_files_without_mutating(tmp_path):
    wheel = tmp_path / "normietext-0.1.0-py3-none-any.whl"
    sdist = tmp_path / "normietext-0.1.0.tar.gz"
    wheel.write_bytes(b"wheel-bytes")
    sdist.write_bytes(b"source-bytes")
    result = checksums(tmp_path)
    assert result.read_text() == "".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in (wheel, sdist)
    )
    assert wheel.read_bytes() == b"wheel-bytes"
    (tmp_path / "other.whl").write_bytes(b"other")
    with pytest.raises(ValueError):
        checksums(tmp_path)
