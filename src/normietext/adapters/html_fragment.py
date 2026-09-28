"""One local Beautiful Soup/lxml conversion with explicit source structure.

HTML recovery does not expose trustworthy raw offsets. DOM identities are stable,
while text and annotations explicitly retain field-level source precision.
"""

import importlib
import re
import warnings
from dataclasses import dataclass, field, replace
from typing import Any

from bs4 import (
    BeautifulSoup,
    Comment,
    Declaration,
    Doctype,
    MarkupResemblesLocatorWarning,
    ProcessingInstruction,
    Tag,
    XMLParsedAsHTMLWarning,
)
from bs4.builder._lxml import LXMLTreeBuilder
from bs4.element import NavigableString

from normietext.adapters._common import DEFAULT_LIMITS, initial, tokenize_lines
from normietext.errors import (
    ErrorCode,
    FormatConversionError,
    InputValidationError,
    ResourceLimitError,
)
from normietext.models import (
    AlignmentSegment,
    Annotation,
    AnnotationKind,
    Association,
    Block,
    BlockKind,
    Edit,
    FieldInput,
    FrozenMap,
    Issue,
    IssueCode,
    Origin,
    OriginPrecision,
    ParsedDocument,
    SourceEvidence,
    SourceFormat,
    Span,
)
from normietext.policy import ResourceLimits
from normietext.provenance import Alignment, TrackedText, stable_id

_WRAPPERS = {"html", "head", "body"}
_EXCLUDED = {"script", "style", "template"}
_CONTAINERS = {
    "div",
    "section",
    "article",
    "main",
    "header",
    "footer",
    "aside",
    "nav",
    "address",
    "figure",
    "blockquote",
    "ul",
    "ol",
    "dl",
    "table",
    "tr",
    "thead",
    "tbody",
    "tfoot",
}
_BLOCKS = _CONTAINERS | {
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "pre",
    "li",
    "dt",
    "dd",
    "td",
    "th",
    "caption",
    "figcaption",
}
_ANNOTATIONS = {
    "a": AnnotationKind.LINK,
    "s": AnnotationKind.STRUCK_TEXT,
    "strike": AnnotationKind.STRUCK_TEXT,
    "del": AnnotationKind.STRUCK_TEXT,
    "sup": AnnotationKind.SUPERSCRIPT,
    "sub": AnnotationKind.SUBSCRIPT,
}
_INTEGER = re.compile(r"[+-]?[0-9]{1,64}\Z")


def _budget(message: str) -> None:
    raise ResourceLimitError(ErrorCode.RESOURCE_LIMIT_EXCEEDED, message)


class _LocalBuilder(LXMLTreeBuilder):
    """Explicit parser settings and early tag/depth gates, before DOM traversal."""

    def __init__(self, limits: ResourceLimits) -> None:
        super().__init__(huge_tree=False, preserve_whitespace_tags=set(_WRAPPERS))
        self.limits = limits
        self.node_count = 0
        self.context_depth = 0
        self.open_names: list[str] = []

    def parser_for(self, encoding: str | None) -> Any:
        etree = importlib.import_module("lxml.etree")
        return etree.HTMLParser(
            target=self,
            encoding=encoding,
            recover=True,
            no_network=True,
            huge_tree=False,
            decompress=False,
            remove_blank_text=False,
            remove_comments=False,
            remove_pis=False,
            collect_ids=False,
        )

    def start(self, tag: Any, attrib: Any, nsmap: Any = None) -> None:
        name = str(tag)
        self.node_count += 1
        self.context_depth += name not in _WRAPPERS
        if self.node_count > self.limits.html_nodes:
            _budget("HTML node budget exceeded during parsing")
        if self.context_depth > self.limits.structural_depth:
            _budget("HTML depth budget exceeded during parsing")
        self.open_names.append(name)
        # Prevent BeautifulSoup.endData from collapsing whitespace-only nodes.
        self.preserve_whitespace_tags.add(name)
        super().start(tag, attrib, {} if nsmap is None else nsmap)

    def end(self, name: Any) -> None:
        super().end(name)
        if self.open_names:
            self.context_depth -= self.open_names.pop() not in _WRAPPERS


def _parse(
    value: str, limits: ResourceLimits
) -> tuple[BeautifulSoup, tuple[dict[str, object], ...]]:
    builder = _LocalBuilder(limits)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", MarkupResemblesLocatorWarning)
            warnings.simplefilter("always", XMLParsedAsHTMLWarning)
            soup = BeautifulSoup(value, builder=builder)
        logs: list[dict[str, object]] = [
            {"warning": item.category.__name__}
            for item in caught
            if item.category is XMLParsedAsHTMLWarning
        ]
        for entry in builder.parser.feed_error_log:
            if entry.level_name == "FATAL":
                raise FormatConversionError(
                    ErrorCode.HTML_PARSE_FAILED, "Fatal HTML parser recovery"
                )
            logs.append(
                {
                    "domain": entry.domain_name,
                    "type": entry.type_name,
                    "level": entry.level_name,
                    "line": entry.line,
                    "column": entry.column,
                }
            )
    except ResourceLimitError, FormatConversionError:
        raise
    except Exception as exc:
        raise FormatConversionError(ErrorCode.HTML_PARSE_FAILED, "HTML conversion failed") from exc
    # Count all DOM nodes, including text and excluded content, before projection.
    for count, _ in enumerate(soup.descendants, 1):
        if count > limits.html_nodes:
            _budget("HTML DOM node budget exceeded")
    return soup, tuple(logs)


def _attribute(tag: Tag, name: str) -> str | None:
    value = tag.get(name)
    return value if isinstance(value, str) else None


@dataclass
class _List:
    id: str
    ordered: bool
    next_ordinal: int
    step: int
    style: str | None


@dataclass
class _Table:
    id: str
    row: int = -1
    column: int = 0
    occupied: dict[int, int] = field(default_factory=dict)


@dataclass
class _Description:
    id: str
    terms: list[str] = field(default_factory=list)
    definitions: list[str] = field(default_factory=list)
    occurrence: int = 0


class _Projection:
    def __init__(self, source: SourceEvidence, limits: ResourceLimits) -> None:
        self.source = source
        self.limits = limits
        self.parts: list[str] = []
        self.length = 0
        self.pending_boundary = False
        self.last = ""
        self.segments: list[AlignmentSegment] = []
        self.blocks: list[Block] = []
        self.annotations: list[Annotation] = []
        self.associations: list[Association] = []
        self.edits: list[Edit] = []
        self.issues: list[Issue] = []
        self.parents: list[str] = []
        self.lists: list[_List] = []
        self.tables: list[_Table] = []
        self.descriptions: list[_Description] = []
        self.node_index = 0
        self.grid_work = 0

    def identity(self, kind: str, origin: Origin, occurrence: int, detail: object = None) -> str:
        return stable_id(
            kind, self.source, "html." + kind, origin, occurrence=occurrence, discriminator=detail
        )

    def append(self, text: str, origin: Origin) -> None:
        if not text:
            return
        if self.length + len(text) > self.limits.output_limit(self.source.source_length):
            raise ResourceLimitError(
                ErrorCode.OUTPUT_LIMIT_EXCEEDED, "HTML projection exceeds budget"
            )
        self.segments.append(AlignmentSegment(Span(self.length, self.length + len(text)), origin))
        self.parts.append(text)
        self.length += len(text)
        self.last = text[-1]

    def flush(self, origin: Origin) -> None:
        if self.pending_boundary and self.length and self.last != "\n":
            self.append("\n", origin)
        self.pending_boundary = False

    def text(self, text: str, origin: Origin) -> None:
        if text:
            self.flush(origin)
            self.append(text, origin)

    def issue(self, origin: Origin, **details: object) -> None:
        self.issues.append(
            Issue(
                IssueCode.INVALID_HTML_ATTRIBUTE,
                "html.attribute",
                origin,
                FrozenMap.from_mapping(details),
            )
        )

    def integer(
        self,
        tag: Tag,
        attribute: str,
        default: int,
        origin: Origin,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int:
        raw = _attribute(tag, attribute)
        if raw is None:
            return default
        text = raw.strip(" \t\r\n\f")
        value = int(text) if _INTEGER.fullmatch(text) else None
        if (
            value is None
            or (minimum is not None and value < minimum)
            or (maximum is not None and value > maximum)
        ):
            self.issue(origin, tag=tag.name, attribute=attribute, value=raw, fallback=default)
            return default
        return value

    def annotation(
        self, kind: AnnotationKind, span: Span, origin: Origin, **payload: object
    ) -> None:
        self.annotations.append(
            Annotation(
                self.identity("annotation", origin, len(self.annotations), kind.value),
                kind,
                "html." + kind.value,
                origin,
                FrozenMap.from_mapping(payload),
                span,
            )
        )

    def close_group(self, group: _Description) -> None:
        if not group.terms and not group.definitions:
            return
        origin = Origin(OriginPrecision.FIELD, source_block_id=group.id)
        self.associations.append(
            Association(
                self.identity("association", origin, group.occurrence),
                tuple(group.terms),
                tuple(group.definitions),
                origin,
                "html.dl/1.0.0",
                group.id,
            )
        )
        group.terms.clear()
        group.definitions.clear()
        group.occurrence += 1

    def cell(self, tag: Tag, origin: Origin) -> dict[str, Any]:
        # Malformed orphan cells keep explicit coordinates in a local synthetic table context.
        table = self.tables[-1] if self.tables else _Table(origin.source_block_id or "orphan", 0)
        if table.row < 0:
            table.row = 0
        colspan = self.integer(tag, "colspan", 1, origin, 1, 1000)
        rowspan = self.integer(tag, "rowspan", 1, origin, 0, 65534)
        if rowspan == 0:
            row = tag.find_parent("tr")
            group = row.parent if row is not None else None
            siblings = group.find_all("tr", recursive=False) if isinstance(group, Tag) else []
            rowspan = len(siblings) - next(
                (i for i, sibling in enumerate(siblings) if sibling is row), len(siblings) - 1
            )
        self.grid_work += colspan
        if self.grid_work > self.limits.html_nodes:
            _budget("HTML table coordinate budget exceeded")
        column = table.column
        while any(table.occupied.get(c, 0) > table.row for c in range(column, column + colspan)):
            column += 1
            if column + colspan > self.limits.html_nodes:
                _budget("HTML table width budget exceeded")
        if column + colspan > self.limits.html_nodes:
            _budget("HTML table width budget exceeded")
        for c in range(column, column + colspan):
            table.occupied[c] = table.row + rowspan
        table.column = column + colspan
        return {
            "row": table.row,
            "column": column,
            "rowspan": rowspan,
            "colspan": colspan,
            "header": tag.name == "th",
        }

    def walk(self, node: Tag | NavigableString) -> None:
        occurrence = self.node_index
        self.node_index += 1
        node_id = self.identity(
            "node",
            Origin(OriginPrecision.FIELD),
            occurrence,
            node.name if isinstance(node, Tag) else "text",
        )
        origin = Origin(OriginPrecision.FIELD, source_block_id=node_id)
        if isinstance(node, (Comment, Doctype, Declaration, ProcessingInstruction)):
            self.edits.append(
                Edit(
                    self.identity("exclude", origin, occurrence),
                    "html.exclude_declaration_or_comment",
                    origin,
                    "",
                )
            )
            return
        if isinstance(node, NavigableString):
            self.text(str(node), origin)
            return
        name = node.name
        if name in _EXCLUDED:
            self.edits.append(
                Edit(
                    self.identity("exclude", origin, occurrence), "html.exclude_" + name, origin, ""
                )
            )
            return
        if name == "br":
            self.pending_boundary = False
            self.append("\n", origin)
            self.blocks.append(
                Block(
                    node_id,
                    BlockKind.LINE,
                    Span(self.length - 1, self.length),
                    origin,
                    parent_id=self.parents[-1] if self.parents else None,
                    origin_tag="br",
                )
            )
            return
        if name == "hr":
            self.pending_boundary = True
            self.blocks.append(
                Block(
                    node_id,
                    BlockKind.LINE,
                    Span(self.length, self.length),
                    origin,
                    parent_id=self.parents[-1] if self.parents else None,
                    origin_tag="hr",
                )
            )
            return
        if name == "img":
            alt = _attribute(node, "alt")
            if alt:
                self.flush(origin)
                start = self.length
                self.append(alt, origin)
                self.annotation(
                    AnnotationKind.ALT_TEXT,
                    Span(start, self.length),
                    origin,
                    alt=alt,
                    src=_attribute(node, "src"),
                )
            return
        explicit_dl_group = (
            name == "div"
            and isinstance(node.parent, Tag)
            and node.parent.name == "dl"
            and bool(self.descriptions)
        )
        if explicit_dl_group:
            self.close_group(self.descriptions[-1])
        structural = name in _BLOCKS or name == "code"
        boundary = name in _BLOCKS
        if boundary:
            self.pending_boundary = True
        # Flush before recording offsets, not after text emission.
        if structural or name in _ANNOTATIONS:
            self.flush(origin)
        start = self.length
        index: int | None = None
        kwargs: dict[str, Any] = {}
        metadata: dict[str, object] = {}
        if structural:
            kind = BlockKind.CONTAINER
            if name in ("p", "caption", "figcaption"):
                kind = BlockKind.PARAGRAPH
            elif name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                kind = BlockKind.HEADING
                kwargs["heading_level"] = int(name[1])
            elif name in ("pre", "code"):
                kind = BlockKind.CODE
            elif name == "li":
                kind = BlockKind.LIST_ITEM
                current = self.lists[-1] if self.lists else None
                kwargs["list_id"] = current.id if current else node_id
                if current and current.ordered:
                    ordinal = self.integer(node, "value", current.next_ordinal, origin)
                    kwargs["ordinal"] = ordinal
                    current.next_ordinal = ordinal + current.step
                kwargs["depth"] = max(0, len(self.lists) - 1)
                style = _attribute(node, "type")
                inherited = current.style if current else None
                if (
                    current
                    and current.ordered
                    and style is not None
                    and style not in ("1", "a", "A", "i", "I")
                ):
                    self.issue(origin, tag=name, attribute="type", value=style, fallback=inherited)
                    style = inherited
                metadata.update(
                    list_style=style if style is not None else inherited,
                    declared_type=_attribute(node, "type"),
                    declared_value=_attribute(node, "value"),
                )
            elif name in ("td", "th"):
                kind = BlockKind.TABLE_CELL
                kwargs.update(self.cell(node, origin))
                metadata["table_id"] = self.tables[-1].id if self.tables else None
                metadata["declared_rowspan"] = _attribute(node, "rowspan")
                metadata["declared_colspan"] = _attribute(node, "colspan")
            elif name in ("dt", "dd"):
                kind = BlockKind.TERM if name == "dt" else BlockKind.DEFINITION
            if name in ("ol", "ul"):
                reversed_list = name == "ol" and node.has_attr("reversed")
                count = len(node.find_all("li", recursive=False))
                first = (
                    self.integer(node, "start", count if reversed_list else 1, origin)
                    if name == "ol"
                    else 1
                )
                style = _attribute(node, "type")
                if name == "ol" and style is not None and style not in ("1", "a", "A", "i", "I"):
                    self.issue(origin, tag=name, attribute="type", value=style, fallback="1")
                    style = "1"
                self.lists.append(
                    _List(node_id, name == "ol", first, -1 if reversed_list else 1, style)
                )
                metadata.update(
                    ordered=name == "ol",
                    reversed=reversed_list,
                    start=first,
                    list_style=style,
                    declared_type=_attribute(node, "type"),
                )
            if name == "table":
                self.tables.append(_Table(node_id))
            if name in ("thead", "tbody", "tfoot") and self.tables:
                self.tables[-1].occupied.clear()
                metadata["table_id"] = self.tables[-1].id
            if name == "tr" and self.tables:
                table = self.tables[-1]
                table.row += 1
                table.column = 0
                metadata.update(table_id=table.id, row=table.row)
            if name == "dl":
                self.descriptions.append(_Description(node_id))
            if name in ("dt", "dd") and self.descriptions:
                group = self.descriptions[-1]
                if name == "dt" and group.definitions:
                    self.close_group(group)
                (group.terms if name == "dt" else group.definitions).append(node_id)
            index = len(self.blocks)
            self.blocks.append(
                Block(
                    node_id,
                    kind,
                    Span(start, start),
                    origin,
                    parent_id=self.parents[-1] if self.parents else None,
                    origin_tag=name,
                    metadata=FrozenMap.from_mapping(metadata),
                    **kwargs,
                )
            )
            self.parents.append(node_id)
        for child in node.children:
            if isinstance(child, (Tag, NavigableString)):
                self.walk(child)
        end = self.length
        if index is not None:
            self.blocks[index] = replace(self.blocks[index], span=Span(start, end))
            self.parents.pop()
        if name in _ANNOTATIONS:
            payload: dict[str, object] = {"tag": name}
            if name == "a":
                payload["href"] = _attribute(node, "href")
            self.annotation(_ANNOTATIONS[name], Span(start, end), origin, **payload)
        if name in ("ol", "ul"):
            self.lists.pop()
        if name == "table":
            self.tables.pop()
        if explicit_dl_group:
            self.close_group(self.descriptions[-1])
        if name == "dl":
            self.close_group(self.descriptions.pop())
        if boundary:
            self.pending_boundary = True

    def finish(self, logs: tuple[dict[str, object], ...]) -> ParsedDocument:
        text = "".join(self.parts)
        # Compose line conversion in output coordinates independently of raw HTML origins.
        local_source = SourceEvidence.from_input(FieldInput(self.source.field, text))
        local = tokenize_lines(TrackedText.from_source(local_source), self.limits)
        raw_alignment = Alignment(self.source.source_length, len(text), tuple(self.segments))
        composed = []
        for segment in local.alignment.segments:
            assert segment.origin.span is not None
            for piece in raw_alignment.slice(segment.origin.span):
                if segment.linear:
                    delta = segment.output.start - segment.origin.span.start
                    composed.append(
                        AlignmentSegment(
                            Span(piece.output.start + delta, piece.output.end + delta), piece.origin
                        )
                    )
            if not segment.linear:
                composed.append(
                    AlignmentSegment(segment.output, raw_alignment.origin_for(segment.origin.span))
                )
        blocks = tuple(
            replace(block, span=local.alignment.project(block.span)) for block in self.blocks
        )
        annotations = tuple(
            replace(item, span=local.alignment.project(item.span))
            for item in self.annotations
            if item.span is not None
        )
        whole = Origin(OriginPrecision.FIELD)
        edits = [
            Edit(self.identity("conversion", whole, 0), "html.convert_once", whole, local.text),
            *self.edits,
        ]
        for index, edit in enumerate(local.edits):
            assert edit.origin.span is not None
            origin = raw_alignment.origin_for(edit.origin.span)
            edits.append(
                Edit(
                    self.identity("line_break", origin, index),
                    edit.rule_id,
                    origin,
                    edit.replacement,
                )
            )
        issues = [
            Issue(
                IssueCode.ORIGIN_PRECISION_REDUCED,
                "html.origin",
                whole,
                FrozenMap.from_mapping({"reason": "parser_has_no_verified_raw_offsets"}),
            ),
            *self.issues,
        ]
        issues.extend(
            Issue(IssueCode.HTML_RECOVERY, "html.parser", whole, FrozenMap.from_mapping(log))
            for log in logs
        )
        return ParsedDocument(
            self.source,
            local.text,
            blocks,
            tuple(self.associations),
            annotations,
            tuple(edits),
            tuple(issues),
            tuple(composed),
        )


def convert(source: FieldInput, limits: ResourceLimits = DEFAULT_LIMITS) -> ParsedDocument:
    tracked = initial(source, limits)
    if source.source_format is not SourceFormat.HTML_FRAGMENT:
        raise InputValidationError(
            ErrorCode.INVALID_FORMAT, "HTML adapter requires declared fragment"
        )
    soup, logs = _parse(source.value, limits)
    projection = _Projection(tracked.source, limits)
    try:
        for child in soup.children:
            if isinstance(child, (Tag, NavigableString)):
                projection.walk(child)
        return projection.finish(logs)
    except RecursionError as exc:
        raise ResourceLimitError(
            ErrorCode.RESOURCE_LIMIT_EXCEEDED, "HTML traversal exceeds host recursion budget"
        ) from exc
