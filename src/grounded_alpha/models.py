from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    url: str
    published_at: date
    accessed_at: date
    quote: str
    source_type: str


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    kind: str
    confidence: float
    source_ids: tuple[str, ...]
    metric: str | None = None
    value: float | None = None
    unit: str | None = None
    period: str | None = None
    counterevidence: str | None = None


@dataclass(frozen=True)
class ResearchPacket:
    subject: str
    as_of: date
    thesis: str
    sources: tuple[Source, ...]
    claims: tuple[Claim, ...]
    risks: tuple[str, ...]


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str
    claim_id: str | None = None
    source_id: str | None = None
    remediation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuditPolicy:
    max_source_age_days: int = 365
    high_confidence_threshold: float = 0.8
    min_risks: int = 2
    min_independent_sources: int = 2
    max_numeric_conflict_ratio: float = 0.05
    fail_below: int = 75

    def validate(self) -> None:
        errors = []
        if self.max_source_age_days < 0:
            errors.append("max_source_age_days must be non-negative")
        if not 0 <= self.high_confidence_threshold <= 1:
            errors.append("high_confidence_threshold must be between 0 and 1")
        if self.min_risks < 0:
            errors.append("min_risks must be non-negative")
        if self.min_independent_sources < 1:
            errors.append("min_independent_sources must be at least 1")
        if self.max_numeric_conflict_ratio < 0:
            errors.append("max_numeric_conflict_ratio must be non-negative")
        if not 0 <= self.fail_below <= 100:
            errors.append("fail_below must be between 0 and 100")
        if errors:
            raise ValueError("; ".join(errors))


@dataclass(frozen=True)
class AuditReport:
    subject: str
    packet_hash: str
    score: int
    passed: bool
    findings: tuple[Finding, ...]
    metrics: dict[str, int | float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "packet_hash": self.packet_hash,
            "score": self.score,
            "passed": self.passed,
            "metrics": self.metrics,
            "findings": [finding.to_dict() for finding in self.findings],
        }
