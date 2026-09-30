"""Conservative evaluation consumers. Candidates are observations, never job facts."""

import json
import re
from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal, localcontext
from enum import Enum
from hashlib import sha256
from typing import Any

from normietext.models import (
    Annotation,
    AnnotationKind,
    Block,
    BlockKind,
    ExtractionStatus,
    JobField,
    NormalizedField,
    NormalizedJobRecord,
    Origin,
    OriginPrecision,
    SourceEvidence,
    Span,
)


@dataclass(frozen=True)
class EvidenceView:
    source: SourceEvidence
    text: str
    blocks: tuple[Block, ...]
    annotations: tuple[Annotation, ...]
    experiment: str = "canonical"

    @classmethod
    def canonical(cls, result: NormalizedField) -> EvidenceView:
        return cls(result.source, result.text, result.blocks, result.annotations)


@dataclass(frozen=True)
class DerivedView:
    """Casefolded matching coordinates map back to canonical codepoint spans."""

    text: str
    positions: tuple[int, ...]

    @classmethod
    def casefold(cls, text: str) -> DerivedView:
        pieces = [char.casefold() for char in text]
        return cls("".join(pieces), tuple(i for i, piece in enumerate(pieces) for _ in piece))

    def canonical_span(self, span: Span) -> Span:
        if not 0 <= span.start < span.end <= len(self.positions):
            raise ValueError("Expected a nonempty derived span")
        return Span(self.positions[span.start], self.positions[span.end - 1] + 1)


@dataclass(frozen=True)
class Context:
    span: Span
    text: str
    role: str
    cues: tuple[str, ...]
    block_ids: tuple[str, ...]
    list_item_ids: tuple[str, ...]
    heading_span: Span | None = None
    heading_text: str | None = None


@dataclass(frozen=True)
class Candidate:
    id: str
    kind: str
    field: JobField
    span: Span
    text: str
    origin: Origin
    context: Context
    value: str
    amounts: tuple[Decimal | None, ...] = ()
    currency: str | None = None
    period: str | None = None
    uncertainty: tuple[str, ...] = ()
    rule: str = "evaluation.literal.v1"
    extraction_state: ExtractionStatus = ExtractionStatus.PRESENT


@dataclass(frozen=True)
class RecordEvidence:
    candidates: tuple[Candidate, ...]
    states: tuple[tuple[str, str, str | None], ...]
    salary: Candidate | None
    type: str | None = None
    seniority: str | None = None
    modality: str | None = None


_TECHNOLOGIES = (
    "C++",
    "C#",
    ".NET",
    "Node.js",
    "CI/CD",
    "Python",
    "Java",
    "JavaScript",
    "SQL",
    "AWS",
    "Azure",
    "GCP",
    "Docker",
    "Kubernetes",
    "Terraform",
    "PyTorch",
    "RAG",
    "LLM",
)
_TECH = re.compile(
    r"(?<![\w])(?:"
    + "|".join(re.escape(t.casefold()) for t in sorted(_TECHNOLOGIES, key=len, reverse=True))
    + r")(?![\w+#])"
)
_AMOUNT = r"\d+(?:[.,]\d+)*(?:[kK])?"
_MONEY = re.compile(
    r"(?<![\w])(?P<currency>USD\s*\$?|US\$|CRC\s*₡?|EUR\s*€?|GBP\s*£?|[$₡€£])\s*"
    r"(?P<first>"
    + _AMOUNT
    + r")(?:\s*[\u2013—-]\s*(?:[$₡€£]\s*)?(?P<second>"
    + _AMOUNT
    + r"))?(?![\w.,])"
)
_PERCENT = re.compile(
    r"(?<![\w])(?P<first>\d+(?:[.,]\d+)?)(?:\s*[\u2013—-]\s*(?P<second>\d+(?:[.,]\d+)?))?\s*%"
)
_PERIOD = re.compile(
    r"(?i)\b(month(?:ly)?|mes|mensual|mês|mensal|year(?:ly)?|annual(?:ly)?|anual|año|ano|hour(?:ly)?|hora|request|query|one-time)\b"
)
_CUES = re.compile(
    r"(?i)\b(?:not|no|não|sin|sem|depending|dependiendo|dependendo|subject to|según|maybe|if|si)\b"
)
_ROLES = (
    ("technical_cost", re.compile(r"(?i)\b(?:cost/query|coste|custo|cost|request|query)\b")),
    ("budget", re.compile(r"(?i)\b(?:budget|presupuesto|orçamento)\b")),
    ("bonus", re.compile(r"(?i)\b(?:bonus|bono|bônus)\b")),
    (
        "base_salary",
        re.compile(r"(?i)\b(?:salary|salario|salário|compensation|remuneración|remuneração)\b"),
    ),
    ("desired", re.compile(r"(?i)\b(?:nice to have|preferred|deseable|desejável|opcional)\b")),
    (
        "required",
        re.compile(r"(?i)\b(?:requirements|requirements-ish|requisitos|required|obligatorio)\b"),
    ),
    (
        "responsibility",
        re.compile(r"(?i)\b(?:responsibilities|responsabilidades|what you.ll be doing)\b"),
    ),
)


def _context(view: EvidenceView, span: Span) -> Context:
    start = view.text.rfind("\n", 0, span.start) + 1
    end = view.text.find("\n", span.end)
    end = len(view.text) if end < 0 else end
    line = view.text[start:end]
    role = next((name for name, pattern in _ROLES if pattern.search(line)), "mentioned")
    heading_span = None
    heading_text = None
    if role == "mentioned":
        # Bounded inherited context requires an explicit short heading; the
        # nearest unrecognized heading resets the role rather than guessing.
        previous = view.text[:start].rstrip("\n").split("\n")
        cursor = len(view.text[:start].rstrip("\n"))
        for earlier in reversed(previous[-12:]):
            earlier_start = cursor - len(earlier)
            cursor = earlier_start - 1
            if earlier.endswith(":") and len(earlier) < 100:
                heading_span = Span(earlier_start, earlier_start + len(earlier))
                heading_text = earlier
                role = next(
                    (name for name, pattern in _ROLES if pattern.search(earlier)), "mentioned"
                )
                break
    blocks = tuple(
        b.id for b in view.blocks if b.span.start <= span.start and span.end <= b.span.end
    )
    items = tuple(b.id for b in view.blocks if b.id in blocks and b.kind is BlockKind.LIST_ITEM)
    cues = tuple(m.group() for m in _CUES.finditer((heading_text or "") + "\n" + line))
    return Context(Span(start, end), line, role, cues, blocks, items, heading_span, heading_text)


def _origin(view: EvidenceView, span: Span) -> Origin:
    containers = [b for b in view.blocks if b.span.start <= span.start and span.end <= b.span.end]
    if not containers:
        return Origin(OriginPrecision.FIELD)
    block = min(containers, key=lambda b: (b.span.end - b.span.start, b.id))
    origin = block.origin
    if origin.span is None:
        return origin
    # Direct comparison at known source offsets proves identity; no searching
    # repeated text and no inference of exactness from equal lengths alone.
    raw = view.source.raw
    if (
        origin.precision is OriginPrecision.EXACT
        and raw is not None
        and raw[origin.span.start : origin.span.end] == view.text[block.span.start : block.span.end]
    ):
        delta = origin.span.start - block.span.start
        return Origin(
            OriginPrecision.EXACT,
            Span(span.start + delta, span.end + delta),
            origin.source_block_id,
        )
    return Origin(OriginPrecision.SEGMENT, origin.span, origin.source_block_id)


def _candidate(
    view: EvidenceView,
    kind: str,
    span: Span,
    value: str,
    *,
    origin: Origin | None = None,
    amounts: tuple[Decimal | None, ...] = (),
    currency: str | None = None,
    period: str | None = None,
    uncertainty: tuple[str, ...] = (),
) -> Candidate:
    context = _context(view, span)
    if kind == "technology":
        before = view.text[context.span.start : span.start]
        after = view.text[span.end : context.span.end]
        if re.search(r"(?i)\b(?:no|not|não|sem)\s+$", before) or re.match(
            r"(?i)\s+(?:is\s+)?(?:not|não)\s+(?:required|obrigatório)", after
        ):
            context = replace(context, role="negated")
    identity = json.dumps(
        [view.source.source_sha256, view.source.field.value, kind, span.start, span.end, value],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return Candidate(
        sha256(identity.encode()).hexdigest(),
        kind,
        view.source.field,
        span,
        view.text[span.start : span.end],
        origin or _origin(view, span),
        context,
        value,
        amounts,
        currency,
        period,
        uncertainty,
    )


def decimal_amount(text: str) -> Decimal | None:
    """Exact, deliberately small grammar; single three-digit separators abstain."""
    multiplier = Decimal(1000) if text[-1:] in ("k", "K") else Decimal(1)
    text = text.rstrip("kK")
    if "," in text and "." in text:
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+\.\d{1,2}", text):
            text = text.replace(",", "")
        elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+,\d{1,2}", text):
            text = text.replace(".", "").replace(",", ".")
        else:
            return None
    elif text.count(",") > 1 or text.count(".") > 1:
        if not re.fullmatch(r"\d{1,3}(?P<sep>[.,])\d{3}(?:(?P=sep)\d{3})+", text):
            return None
        text = text.replace(",", "").replace(".", "")
    elif re.fullmatch(r"[1-9]\d*[.,]\d{3}", text):
        return None
    else:
        text = text.replace(",", ".")
    with localcontext() as context:
        context.prec = max(28, len(text) + 6)
        return Decimal(text) * multiplier


def collect(view: EvidenceView | NormalizedField) -> tuple[Candidate, ...]:
    if isinstance(view, NormalizedField):
        view = EvidenceView.canonical(view)
    candidates = []
    derived = DerivedView.casefold(view.text)
    for match in _TECH.finditer(derived.text):
        span = derived.canonical_span(Span(*match.span()))
        candidates.append(_candidate(view, "technology", span, match.group()))
    for annotation in view.annotations:
        if (
            annotation.kind in (AnnotationKind.EMOJI_REGION, AnnotationKind.EMOJI_SUBDIVISION)
            and annotation.span is not None
        ):
            candidates.append(
                _candidate(
                    view,
                    "region",
                    annotation.span,
                    str(annotation.payload["value"]),
                    origin=annotation.origin,
                )
            )
    for pattern, kind in ((_MONEY, "money"), (_PERCENT, "percentage")):
        for match in pattern.finditer(view.text):
            span = Span(*match.span())
            amounts = tuple(
                decimal_amount(v) for v in (match["first"], match["second"]) if v is not None
            )
            currency = None
            if kind == "money":
                glyph = match["currency"].strip()
                currency = (
                    "USD"
                    if glyph.startswith(("USD", "US$"))
                    else "CRC"
                    if glyph.startswith(("CRC", "₡"))
                    else "EUR"
                    if glyph.startswith(("EUR", "€"))
                    else "GBP"
                    if glyph.startswith(("GBP", "£"))
                    else None
                )
            context = _context(view, span)
            period_match = _PERIOD.search(view.text[span.end : context.span.end])
            period = period_match.group().casefold() if period_match else None
            uncertainty: tuple[str, ...] = (
                () if all(a is not None for a in amounts) else ("ambiguous_numeric_separator",)
            )
            if kind == "money" and currency is None:
                uncertainty += ("currency_unspecified",)
            candidates.append(
                _candidate(
                    view,
                    kind,
                    span,
                    match.group(),
                    amounts=amounts,
                    currency=currency,
                    period=period,
                    uncertainty=uncertainty,
                )
            )
    return tuple(sorted(candidates, key=lambda c: (c.span.start, c.span.end, c.kind, c.id)))


def collect_record(record: NormalizedJobRecord) -> RecordEvidence:
    candidates = tuple(
        c for item in record.fields if item.result is not None for c in collect(item.result)
    )
    states = tuple(
        (
            item.field.value,
            item.input.state.value,
            item.failure.code.value
            if item.failure
            else item.input.error.code
            if item.input.error
            else None,
        )
        for item in record.fields
    )
    salaries = [c for c in candidates if c.kind == "money" and c.context.role == "base_salary"]
    # Contradictory/alternative complete amounts never silently select a winner.
    salary = (
        salaries[0]
        if (
            len(salaries) == 1
            and salaries[0].currency is not None
            and salaries[0].period is not None
            and not salaries[0].uncertainty
            and not salaries[0].context.cues
        )
        else None
    )
    return RecordEvidence(candidates, states, salary)


def wire(value: Any) -> Any:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Nonfinite Decimal")
        return format(value, "f")
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: wire(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, (list, tuple)):
        return [wire(item) for item in value]
    if isinstance(value, dict):
        return {str(k): wire(v) for k, v in value.items()}
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"Unsupported evaluation wire type: {type(value).__name__}")


def evidence_bytes(value: object) -> bytes:
    return json.dumps(
        wire(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
