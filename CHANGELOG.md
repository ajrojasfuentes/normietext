# Changelog

## [0.1.0] - 2026-10-04

First public release of the MIT-licensed Python library for deterministic normalization of scraped job text.

### Added

- Field, six-field record and text-only APIs with explicit source formats and typed failures.
- HTML structure conversion, encoding repair, Unicode NFC, emoji hints, conservative list normalization and technical-text preservation.
- Recoverable source evidence, provenance, annotations, attributed edits, canonical serialization and typed reentry.
- Optional operational measurements, resource limits, synthetic quality evaluation and batch benchmarks.
- GitHub wheel and source distributions with SHA256SUMS, packaged policy data, licenses and Python typing metadata.

### Fixed

- Preserve separators between consecutive empty HTML cells and reject inconsistent canonical parent spans.
- Bound pictogram matching and NFC processing to avoid unnecessary timeouts on the accepted adversarial corpus.
- Guard Unix resource APIs so benchmark typing and execution handle Windows correctly; unavailable RSS is reported as null.

### Compatibility and limitations

- CPython >=3.14,<3.15; reference runtime 3.14.7. Package 0.1.0, schema 1.0.0, rules 1.0.1, profile linkedin_jobs_aggressive_v1.
- No network or LLM calls during normalization. No scraping, semantic parsing, salary resolution or hosted service.
- HTML provenance remains field-level where exact raw offsets cannot be demonstrated.
- Quality and adoption evidence is synthetic. Batch capacity is hardware- and corpus-dependent, and estimates for 100,000 jobs are extrapolations.
- Detailed per-Unicode-class invisible counts and emoji percentages with explicit denominators remain outside the current operational metrics.
- Dependencies and bundled data retain their respective licenses. PyPI publication is not part of this release.

Download the wheel and SHA256SUMS, verify the digest, then install the wheel in a compatible Python environment. Retain raw inputs and the runtime manifest for replay and rollback.

[0.1.0]: https://github.com/ajrojasfuentes/normietext/releases/tag/v0.1.0
