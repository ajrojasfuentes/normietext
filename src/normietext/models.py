"""Immutable domain contracts. These models do not normalize or interpret text."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from normietext._validation import Validated, require, valid_text
from normietext.errors import ErrorCode, InputValidationError


class JobField(StrEnum):
    JOB_TITLE = "job_title"
    JOB_DESCRIPTION = "job_description"
    JOB_CRITERIA_LIST = "job_criteria_list"
    JOB_TYPE = "job_type"
    SENIORITY = "seniority"
    RAW_LOCATION = "raw_location"


class SourceFormat(StrEnum):
    PLAIN_TEXT = "plain_text"
    HTML_FRAGMENT = "html_fragment"
    HTML_ESCAPED_TEXT = "html_escaped_text"
    UNKNOWN = "unknown"


class ExtractionStatus(StrEnum):
    PRESENT = "present"
    MISSING = "missing"
    EXTRACTION_ERROR = "extraction_error"


class FieldStatus(StrEnum):
    OK = "ok"
    OK_WITH_ISSUES = "ok_with_issues"
    EMPTY = "empty"


class RecordStatus(StrEnum):
    OK = "ok"
    PARTIAL = "partial"
    MISSING = "missing"


class DocumentPhase(StrEnum):
    CONVERTED = "converted"
    CANONICAL = "canonical"


class OriginPrecision(StrEnum):
    EXACT = "exact"
    SEGMENT = "segment"
    FIELD = "field"


class BlockKind(StrEnum):
    PARAGRAPH = "paragraph"
    LINE = "line"
    HEADING = "heading"
    LIST_ITEM = "list_item"
    TABLE_CELL = "table_cell"
    CODE = "code"
    TERM = "term"
    DEFINITION = "definition"


class AnnotationKind(StrEnum):
    EMOJI_REGION = "emoji_region"
    EMOJI_SUBDIVISION = "emoji_subdivision"
    EMOJI_HINT = "emoji_hint"
    ALT_TEXT = "alt_text"
    STRUCK_TEXT = "struck_text"
    LINK = "link"
    SUPERSCRIPT = "superscript"
    SUBSCRIPT = "subscript"


class IssueCode(StrEnum):
    SOURCE_FORMAT_UNKNOWN = "SOURCE_FORMAT_UNKNOWN"
    REPLACEMENT_CHARACTER_PRESENT = "REPLACEMENT_CHARACTER_PRESENT"
    PROTECTED_SPAN_MODIFIED = "PROTECTED_SPAN_MODIFIED"
    ORIGIN_PRECISION_REDUCED = "ORIGIN_PRECISION_REDUCED"
    UNCLASSIFIED_SYMBOL_SEQUENCE = "UNCLASSIFIED_SYMBOL_SEQUENCE"
    INVALID_REGION_SEQUENCE = "INVALID_REGION_SEQUENCE"
    INVALID_HTML_ATTRIBUTE = "INVALID_HTML_ATTRIBUTE"
    HTML_RECOVERY = "HTML_RECOVERY"
    LIST_ORDINAL_CONFLICT = "LIST_ORDINAL_CONFLICT"


type JSONValue = bool | int | float | str | tuple[JSONValue, ...] | FrozenMap | None


@dataclass(frozen=True, slots=True)
class FrozenMap(Mapping[str, JSONValue]):
    """A detached, recursively immutable JSON object; no mutable payload aliases."""

    entries: tuple[tuple[str, JSONValue], ...] = ()

    def __post_init__(self) -> None:
        require(type(self.entries) is tuple, "Object entries must be a tuple")
        names: set[str] = set()
        for entry in self.entries:
            require(type(entry) is tuple and len(entry) == 2, "Invalid object entry")
            key, value = entry
            require(type(key) is str and valid_text(key), "Invalid JSON key")
            require(key not in names, "Duplicate JSON key")
            names.add(key)
            _check_json(value, 0)

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> FrozenMap:
        result = freeze_json(value)
        require(isinstance(result, FrozenMap), "Expected an object")
        assert isinstance(result, FrozenMap)
        return result

    def __getitem__(self, key: str) -> JSONValue:
        for name, value in self.entries:
            if name == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (name for name, _ in self.entries)

    def __len__(self) -> int:
        return len(self.entries)


def _check_json(value: object, depth: int) -> None:
    require(depth <= 64, "JSON nesting exceeds 64")
    if value is None or type(value) in (bool, int):
        return
    if type(value) is str:
        require(valid_text(value), "Invalid JSON Unicode")
    elif type(value) is float:
        require(isfinite(value), "Nonfinite JSON number")
    elif type(value) is tuple:
        for item in value:
            _check_json(item, depth + 1)
    elif isinstance(value, FrozenMap):
        for _, item in value.entries:
            _check_json(item, depth + 1)
    else:
        require(False, "Payload must contain immutable JSON values")


def freeze_json(value: object, *, _depth: int = 0) -> JSONValue:
    require(_depth <= 64, "JSON nesting exceeds 64 (or contains a cycle)")
    if isinstance(value, Mapping):
        pairs: list[tuple[str, JSONValue]] = []
        for key, item in value.items():
            require(type(key) is str, "JSON keys must be strings")
            pairs.append((key, freeze_json(item, _depth=_depth + 1)))
        return FrozenMap(tuple(pairs))
    if isinstance(value, (list, tuple)):
        return tuple(freeze_json(item, _depth=_depth + 1) for item in value)
    _check_json(value, _depth)
    assert value is None or isinstance(value, (str, bool, int, float))
    return value


@dataclass(frozen=True, slots=True)
class Span(Validated):
    start: int
    end: int

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        require(0 <= self.start <= self.end, "Invalid half-open span")

    def within(self, text: str) -> bool:
        return self.end <= len(text)


@dataclass(frozen=True, slots=True)
class FieldInput(Validated):
    field: JobField
    value: str
    source_format: SourceFormat = SourceFormat.PLAIN_TEXT
    source_ref: str | None = None
    source_adapter_version: str | None = None

    def __post_init__(self) -> None:
        for ok, code in (
            (isinstance(self.field, JobField), ErrorCode.INVALID_FIELD),
            (isinstance(self.source_format, SourceFormat), ErrorCode.INVALID_FORMAT),
            (type(self.value) is str, ErrorCode.INVALID_TYPE),
        ):
            if not ok:
                raise InputValidationError(code, "Invalid field input")
        if not valid_text(self.value):
            raise InputValidationError(ErrorCode.INVALID_UNICODE, "Isolated surrogate in input")
        Validated.__post_init__(self)
        require(self.source_ref is None or bool(self.source_ref), "Empty source reference")
        require(
            self.source_adapter_version is None or bool(self.source_adapter_version),
            "Empty adapter version",
        )


@dataclass(frozen=True, slots=True)
class ExtractionError(Validated):
    code: str
    message: str
    source_ref: str | None = None

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        require(bool(self.code), "Extraction error needs a code")


@dataclass(frozen=True, slots=True)
class InputField(Validated):
    field: JobField
    state: ExtractionStatus
    source: FieldInput | None = None
    error: ExtractionError | None = None

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        if self.state is ExtractionStatus.PRESENT:
            require(self.source is not None and self.error is None, "Present needs only source")
            assert self.source is not None
            require(self.source.field is self.field, "Field/source mismatch")
        elif self.state is ExtractionStatus.MISSING:
            require(self.source is None and self.error is None, "Missing cannot contain a value")
        else:
            require(self.source is None and self.error is not None, "Extraction error needs error")


def _six_fields(values: tuple[InputField, ...] | tuple[FieldOutcome, ...]) -> None:
    require(len(values) == 6, "Exactly six fields required")
    require(
        tuple(item.field for item in values) == tuple(JobField), "Wrong field order or duplicate"
    )


@dataclass(frozen=True, slots=True)
class JobInputRecord(Validated):
    fields: tuple[InputField, ...]

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        _six_fields(self.fields)

    @classmethod
    def from_mapping(cls, values: Mapping[str, InputField]) -> JobInputRecord:
        if not isinstance(values, Mapping) or set(values) != {field.value for field in JobField}:
            raise InputValidationError(ErrorCode.INVALID_RECORD, "Require exactly six known keys")
        entries = tuple(values[field.value] for field in JobField)
        for field, entry in zip(JobField, entries, strict=True):
            require(isinstance(entry, InputField) and entry.field is field, "Field/key mismatch")
        return cls(entries)


@dataclass(frozen=True, slots=True)
class SourceEvidence(Validated):
    field: JobField
    source_format: SourceFormat
    source_length: int
    raw: str | None = None
    source_ref: str | None = None
    source_adapter_version: str | None = None

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        require(self.source_length >= 0, "Negative source length")
        require(self.raw is not None or bool(self.source_ref), "Recoverable source required")
        require(self.source_ref is None or bool(self.source_ref), "Empty source reference")
        if self.raw is not None:
            require(len(self.raw) == self.source_length, "Raw length mismatch")

    @classmethod
    def from_input(cls, source: FieldInput) -> SourceEvidence:
        return cls(
            source.field,
            source.source_format,
            len(source.value),
            source.value,
            source.source_ref,
            source.source_adapter_version,
        )


@dataclass(frozen=True, slots=True)
class Origin(Validated):
    precision: OriginPrecision
    span: Span | None = None
    source_block_id: str | None = None

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        require(
            (self.precision is OriginPrecision.FIELD) == (self.span is None),
            "Exact/segment origins require a span; field origins have no positional claim",
        )


@dataclass(frozen=True, slots=True)
class Block(Validated):
    id: str
    kind: BlockKind
    span: Span
    origin: Origin
    parent_id: str | None = None
    list_id: str | None = None
    ordinal: int | None = None
    depth: int = 0
    row: int | None = None
    column: int | None = None
    rowspan: int = 1
    colspan: int = 1
    heading_level: int | None = None
    origin_tag: str | None = None
    header: bool = False

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        require(bool(self.id) and self.depth >= 0, "Invalid block ID/depth")
        require(self.rowspan >= 1 and self.colspan >= 1, "Invalid cell extent")
        require(self.parent_id != self.id, "Block cannot parent itself")
        if self.kind is BlockKind.LIST_ITEM:
            require(bool(self.list_id), "List item needs list ID")
        else:
            require(self.ordinal is None, "Only a list item has an ordinal")
        if self.kind is BlockKind.TABLE_CELL:
            require(self.row is not None and self.column is not None, "Cell coordinates required")
            assert self.row is not None and self.column is not None
            require(self.row >= 0 and self.column >= 0, "Negative cell coordinate")
        else:
            require(self.row is None and self.column is None, "Non-cell coordinates")
            require(not self.header and self.rowspan == self.colspan == 1, "Non-cell metadata")
        if self.kind is BlockKind.HEADING:
            require(self.heading_level in range(1, 7), "Heading level must be 1-6")
        else:
            require(self.heading_level is None, "Non-heading level")


@dataclass(frozen=True, slots=True)
class Association(Validated):
    """An explicit group: multiple terms/definitions, not a guessed one-to-one pair."""

    id: str
    term_ids: tuple[str, ...]
    definition_ids: tuple[str, ...]
    origin: Origin
    source_contract: str
    parent_id: str | None = None

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        require(bool(self.id) and bool(self.source_contract), "Association needs identity/contract")
        require(bool(self.term_ids or self.definition_ids), "Empty association")
        ids = self.term_ids + self.definition_ids
        require(len(ids) == len(set(ids)) and all(ids), "Duplicate/empty association members")


@dataclass(frozen=True, slots=True)
class Annotation(Validated):
    id: str
    kind: AnnotationKind
    rule_id: str
    origin: Origin
    payload: FrozenMap = FrozenMap()
    span: Span | None = None
    rendered_token: str | None = None

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        require(bool(self.id) and bool(self.rule_id), "Annotation needs identity/rule")
        require(self.rendered_token is None or self.span is not None, "Visible token needs span")


@dataclass(frozen=True, slots=True)
class Edit(Validated):
    id: str
    rule_id: str
    origin: Origin
    replacement: str

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        require(bool(self.id) and bool(self.rule_id), "Edit needs identity/rule")


@dataclass(frozen=True, slots=True)
class Issue(Validated):
    code: IssueCode
    rule_id: str
    origin: Origin
    details: FrozenMap = FrozenMap()

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        require(bool(self.rule_id), "Issue needs a rule")


@dataclass(frozen=True, slots=True)
class VersionedArtifact(Validated):
    name: str
    version: str
    sha256: str

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        require(bool(self.name) and bool(self.version), "Artifact needs name/version")
        require(
            len(self.sha256) == 64 and all(c in "0123456789abcdef" for c in self.sha256),
            "Invalid SHA-256",
        )


@dataclass(frozen=True, slots=True)
class Manifest(Validated):
    """Manifest shape only; effective manifest generation belongs to phase 2."""

    schema_version: str
    normalization_version: str
    policy_id: str
    policy_hash: str
    code_revision: str
    python_version: str
    unicode_version: str
    backend: str
    libxml2_version: str
    dependencies: tuple[tuple[str, str], ...]
    tables: tuple[VersionedArtifact, ...]
    runtime_artifacts: tuple[VersionedArtifact, ...]

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        for name in (
            "schema_version",
            "normalization_version",
            "policy_id",
            "code_revision",
            "python_version",
            "unicode_version",
            "backend",
            "libxml2_version",
        ):
            require(bool(getattr(self, name)), f"Empty manifest {name}")
        require(
            len(self.policy_hash) == 64 and all(c in "0123456789abcdef" for c in self.policy_hash),
            "Invalid policy hash",
        )
        require(
            len({name for name, _ in self.dependencies}) == len(self.dependencies),
            "Duplicate dependencies",
        )
        require(all(name and version for name, version in self.dependencies), "Empty dependency")
        for artifacts in (self.tables, self.runtime_artifacts):
            require(len({item.name for item in artifacts}) == len(artifacts), "Duplicate artifacts")


def _document_links(
    text: str,
    source: SourceEvidence,
    blocks: tuple[Block, ...],
    associations: tuple[Association, ...],
    annotations: tuple[Annotation, ...],
    edits: tuple[Edit, ...],
    issues: tuple[Issue, ...],
) -> None:
    by_id = {block.id: block for block in blocks}
    for collection in (blocks, associations, annotations, edits):
        require(len({item.id for item in collection}) == len(collection), "Duplicate IDs")
    for block in blocks:
        require(block.span.within(text), "Block outside text")
        seen = {block.id}
        parent = block.parent_id
        while parent is not None:
            require(parent in by_id and parent not in seen, "Missing/cyclic block parent")
            seen.add(parent)
            parent = by_id[parent].parent_id
    for association in associations:
        require(
            association.parent_id is None or association.parent_id in by_id,
            "Missing association parent",
        )
        for ids, kind in (
            (association.term_ids, BlockKind.TERM),
            (association.definition_ids, BlockKind.DEFINITION),
        ):
            require(
                all(key in by_id and by_id[key].kind is kind for key in ids),
                "Association references wrong block kind",
            )
    for item in annotations:
        require(item.span is None or item.span.within(text), "Annotation outside text")
        if item.rendered_token is not None:
            assert item.span is not None
            require(
                text[item.span.start : item.span.end] == item.rendered_token, "Token/span mismatch"
            )
    entries: tuple[Block | Association | Annotation | Edit | Issue, ...] = (
        *blocks,
        *associations,
        *annotations,
        *edits,
        *issues,
    )
    for entry in entries:
        origin = entry.origin
        require(
            origin.span is None or origin.span.end <= source.source_length, "Origin outside source"
        )


@dataclass(frozen=True, slots=True)
class ParsedDocument(Validated):
    """Converted once, with source-stage offsets; not yet repaired or canonical."""

    source: SourceEvidence
    text: str
    blocks: tuple[Block, ...] = ()
    associations: tuple[Association, ...] = ()
    annotations: tuple[Annotation, ...] = ()
    edits: tuple[Edit, ...] = ()
    issues: tuple[Issue, ...] = ()

    @property
    def phase(self) -> DocumentPhase:
        return DocumentPhase.CONVERTED

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        _document_links(
            self.text,
            self.source,
            self.blocks,
            self.associations,
            self.annotations,
            self.edits,
            self.issues,
        )


@dataclass(frozen=True, slots=True)
class NormalizedField(Validated):
    """Canonical result envelope; full policy invariants are checked by the future pipeline."""

    source: SourceEvidence
    text: str
    manifest: Manifest
    blocks: tuple[Block, ...] = ()
    associations: tuple[Association, ...] = ()
    annotations: tuple[Annotation, ...] = ()
    edits: tuple[Edit, ...] = ()
    issues: tuple[Issue, ...] = ()

    @property
    def field(self) -> JobField:
        return self.source.field

    @property
    def source_format(self) -> SourceFormat:
        return self.source.source_format

    @property
    def phase(self) -> DocumentPhase:
        return DocumentPhase.CANONICAL

    @property
    def status(self) -> FieldStatus:
        if not self.text:
            return FieldStatus.EMPTY
        return FieldStatus.OK_WITH_ISSUES if self.issues else FieldStatus.OK

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        _document_links(
            self.text,
            self.source,
            self.blocks,
            self.associations,
            self.annotations,
            self.edits,
            self.issues,
        )


@dataclass(frozen=True, slots=True)
class FieldFailure(Validated):
    """Retains the input envelope rather than substituting an empty normalized field."""

    source: FieldInput
    code: ErrorCode
    message: str


@dataclass(frozen=True, slots=True)
class FieldOutcome(Validated):
    input: InputField
    result: NormalizedField | None = None
    failure: FieldFailure | None = None

    @property
    def field(self) -> JobField:
        return self.input.field

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        if self.input.state is ExtractionStatus.PRESENT:
            require(
                (self.result is None) != (self.failure is None), "One result or failure required"
            )
            if self.result is not None:
                require(self.result.field is self.field, "Result field mismatch")
                assert self.input.source is not None
                evidence = self.result.source
                require(evidence.source_ref == self.input.source.source_ref, "Result ref mismatch")
                require(
                    evidence.source_adapter_version == self.input.source.source_adapter_version,
                    "Result adapter mismatch",
                )
                require(
                    evidence.source_format is self.input.source.source_format,
                    "Result format mismatch",
                )
                require(
                    evidence.source_length == len(self.input.source.value), "Result length mismatch"
                )
                if evidence.raw is not None:
                    require(evidence.raw == self.input.source.value, "Result raw mismatch")
                else:
                    require(
                        evidence.source_ref == self.input.source.source_ref, "Result ref mismatch"
                    )
            if self.failure is not None:
                require(self.failure.source == self.input.source, "Failure/source mismatch")
        else:
            require(
                self.result is None and self.failure is None, "Absent field cannot be normalized"
            )


@dataclass(frozen=True, slots=True)
class NormalizedJobRecord(Validated):
    fields: tuple[FieldOutcome, ...]

    @property
    def status(self) -> RecordStatus:
        if all(item.input.state is ExtractionStatus.MISSING for item in self.fields):
            return RecordStatus.MISSING
        if any(
            item.failure is not None or item.input.state is not ExtractionStatus.PRESENT
            for item in self.fields
        ):
            return RecordStatus.PARTIAL
        return RecordStatus.OK

    def __post_init__(self) -> None:
        Validated.__post_init__(self)
        _six_fields(self.fields)
