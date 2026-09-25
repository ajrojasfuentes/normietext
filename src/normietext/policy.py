"""Validated, immutable configuration for the initial normative profile."""

from dataclasses import dataclass, fields, is_dataclass
from typing import cast, get_type_hints

from normietext._validation import Validated, require
from normietext.errors import ErrorCode, ModelValidationError, PolicyValidationError
from normietext.models import JobField


@dataclass(frozen=True, slots=True)
class InputPolicy(Validated):
    default_format: str = "plain_text"
    auto_detect_html: bool = False
    require_recoverable_source: bool = True
    reject_surrogates: bool = True


@dataclass(frozen=True, slots=True)
class EncodingPolicy(Validated):
    operation: str = "fix_encoding"
    restore_byte_a0: bool = False
    replace_lossy_sequences: bool = False
    decode_inconsistent_utf8: bool = True
    fix_c1_controls: bool = True


@dataclass(frozen=True, slots=True)
class UnicodePolicy(Validated):
    normalization: str = "NFC"
    final_normalization: bool = True
    remove_cf: bool = True
    remove_default_ignorables: bool = True
    remove_cc_except_lf: bool = True
    remove_braille_blank: bool = True


@dataclass(frozen=True, slots=True)
class EmojiPolicy(Validated):
    default_action: str = "remove"
    region_flags: str = "token_and_annotation"
    subdivision_flags: str = "token_and_annotation"
    hints: tuple[str, ...] = (
        "money_bag",
        "round_pushpin",
        "warning",
        "check_mark_button",
        "cross_mark",
    )
    protected_text_symbols: tuple[str, ...] = ("copyright", "registered", "trademark")
    keycaps: str = "preserve_base_or_list_ordinal"


@dataclass(frozen=True, slots=True)
class WhitespacePolicy(Validated):
    horizontal: str = "ascii_space"
    collapse_runs: bool = True
    strip_each_line: bool = True
    preserve_indentation: bool = False
    max_blank_lines: int = 1
    strip_field: bool = True


@dataclass(frozen=True, slots=True)
class PunctuationPolicy(Validated):
    global_dash_folding: bool = False
    global_quote_folding: bool = False
    fullwidth_solidus_in_ordinary_text: bool = True


@dataclass(frozen=True, slots=True)
class StructurePolicy(Validated):
    plain_text_lists_in: tuple[str, ...] = ("job_description", "job_criteria_list")
    preserve_ordinals: bool = True
    metadata_before_spacing: bool = True


@dataclass(frozen=True, slots=True)
class OutputPolicy(Validated):
    compact_fields: tuple[str, ...] = ("job_title", "job_type", "seniority", "raw_location")
    multiline_fields: tuple[str, ...] = ("job_description", "job_criteria_list")
    generated_tokens_require_annotations: bool = True
    trace_snapshots: bool = False


@dataclass(frozen=True, slots=True)
class ResourceLimits(Validated):
    job_title: int = 8192
    job_description: int = 262144
    job_criteria_list: int = 32768
    job_type: int = 4096
    seniority: int = 4096
    raw_location: int = 8192
    record: int = 327680
    html_nodes: int = 20000
    structural_depth: int = 128
    output_floor: int = 1024
    max_expansion_factor: int = 32
    regex_timeout_ms: int = 50

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        require(
            all(getattr(self, field.name) > 0 for field in fields(self)), "Limits must be positive"
        )
        require(self.max_expansion_factor >= 32, "Initial profile requires expansion factor >=32")

    def for_field(self, field: JobField) -> int:
        require(isinstance(field, JobField), "Unknown job field")
        result: int = getattr(self, field.value)
        return result

    def output_limit(self, raw_length: int) -> int:
        require(type(raw_length) is int and raw_length >= 0, "Invalid source length")
        return max(self.output_floor, self.max_expansion_factor * raw_length)


@dataclass(frozen=True, slots=True)
class NormalizationPolicy(Validated):
    policy_id: str = "linkedin_jobs_aggressive_v1"
    schema_version: str = "1.0.0"
    normalization_version: str = "1.0.0"
    input: InputPolicy = InputPolicy()
    encoding: EncodingPolicy = EncodingPolicy()
    unicode: UnicodePolicy = UnicodePolicy()
    emoji: EmojiPolicy = EmojiPolicy()
    whitespace: WhitespacePolicy = WhitespacePolicy()
    punctuation: PunctuationPolicy = PunctuationPolicy()
    structure: StructurePolicy = StructurePolicy()
    output: OutputPolicy = OutputPolicy()
    limits: ResourceLimits = ResourceLimits()

    def __post_init__(self) -> None:
        try:
            Validated.__post_init__(self)
            require(self.policy_id == "linkedin_jobs_aggressive_v1", "Unsupported profile")
            require(
                self.schema_version == self.normalization_version == "1.0.0",
                "Unsupported initial version",
            )
            for name in (
                "input",
                "encoding",
                "unicode",
                "emoji",
                "whitespace",
                "punctuation",
                "structure",
                "output",
            ):
                section = getattr(self, name)
                require(section == type(section)(), f"Unsupported behavior in {name}")
        except ModelValidationError as exc:
            raise PolicyValidationError(ErrorCode.INVALID_POLICY, str(exc)) from exc

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> NormalizationPolicy:
        """Accept a JSON-style object, reject unknown keys and implicit scalar coercions."""
        try:
            return _from_dict(cls, data)
        except (ModelValidationError, TypeError) as exc:
            raise PolicyValidationError(ErrorCode.INVALID_POLICY, str(exc)) from exc


def _from_dict[T: Validated](cls: type[T], data: dict[str, object]) -> T:
    require(type(data) is dict, "Configuration must be an object")
    hints = get_type_hints(cls)
    require(set(data) <= set(hints), "Unknown configuration option")
    values: dict[str, object] = {}
    for key, value in data.items():
        kind = hints[key]
        if isinstance(kind, type) and is_dataclass(kind):
            require(type(value) is dict, f"Expected object for {key}")
            assert isinstance(value, dict)
            values[key] = _from_dict(cast(type[Validated], kind), value)
        elif isinstance(value, list):
            values[key] = tuple(value)
        else:
            values[key] = value
    return cls(**values)
