import hashlib
import json
from collections import defaultdict
from urllib.parse import urlparse

from grounded_alpha.models import (
    AuditPolicy,
    AuditReport,
    Finding,
    ResearchPacket,
    Severity,
)
from grounded_alpha.parser import parse_packet

SEVERITY_PENALTIES = {
    Severity.ERROR: 18,
    Severity.WARNING: 7,
    Severity.INFO: 1,
}


def audit_packet(
    raw: dict[str, object], policy: AuditPolicy | None = None
) -> AuditReport:
    active_policy = policy or AuditPolicy()
    active_policy.validate()
    packet = parse_packet(raw)
    findings = _run_checks(packet, active_policy)
    score = max(
        0,
        100 - sum(SEVERITY_PENALTIES[finding.severity] for finding in findings),
    )
    passed = score >= active_policy.fail_below and not any(
        finding.severity is Severity.ERROR for finding in findings
    )
    return AuditReport(
        subject=packet.subject,
        packet_hash=_packet_hash(raw),
        score=score,
        passed=passed,
        findings=tuple(findings),
        metrics=_metrics(packet),
    )


def _run_checks(packet: ResearchPacket, policy: AuditPolicy) -> list[Finding]:
    findings: list[Finding] = []
    sources = {source.id: source for source in packet.sources}
    referenced_source_ids: set[str] = set()

    if not packet.claims:
        findings.append(
            Finding(
                code="no_claims",
                severity=Severity.ERROR,
                message="The packet contains no auditable claims.",
                remediation="Add explicit claims with confidence and provenance.",
            )
        )

    if len(packet.risks) < policy.min_risks:
        findings.append(
            Finding(
                code="insufficient_risks",
                severity=Severity.WARNING,
                message=(
                    f"The thesis names {len(packet.risks)} risks; policy requires "
                    f"{policy.min_risks}."
                ),
                remediation="Add concrete conditions that could invalidate the thesis.",
            )
        )

    for claim in packet.claims:
        referenced_source_ids.update(claim.source_ids)
        claim_sources = [sources[item] for item in claim.source_ids if item in sources]
        missing_ids = sorted(set(claim.source_ids) - sources.keys())
        if missing_ids:
            findings.append(
                Finding(
                    code="unknown_source",
                    severity=Severity.ERROR,
                    claim_id=claim.id,
                    message=(
                        f"Claim references unknown sources: {', '.join(missing_ids)}."
                    ),
                    remediation=(
                        "Add each source to the packet or remove its identifier."
                    ),
                )
            )
        if claim.kind in {"fact", "estimate"} and not claim.source_ids:
            findings.append(
                Finding(
                    code="uncited_claim",
                    severity=Severity.ERROR,
                    claim_id=claim.id,
                    message=f"{claim.kind.title()} claim has no source.",
                    remediation=(
                        "Cite at least one source that directly supports the claim."
                    ),
                )
            )

        if (claim.metric or claim.value is not None) and any(
            value is None for value in (claim.value, claim.unit, claim.period)
        ):
            findings.append(
                Finding(
                    code="incomplete_metric",
                    severity=Severity.WARNING,
                    claim_id=claim.id,
                    message="Numeric claim is missing value, unit, or period metadata.",
                    remediation=(
                        "Provide value, unit, and period for reproducible comparison."
                    ),
                )
            )

        if claim.confidence >= policy.high_confidence_threshold:
            domains = {_source_domain(source.url) for source in claim_sources}
            if len(domains) < policy.min_independent_sources:
                findings.append(
                    Finding(
                        code="weak_high_confidence_support",
                        severity=Severity.WARNING,
                        claim_id=claim.id,
                        message=(
                            f"High-confidence claim has {len(domains)} independent "
                            "source domains."
                        ),
                        remediation=(
                            "Cite at least "
                            f"{policy.min_independent_sources} independent sources or "
                            "lower confidence."
                        ),
                    )
                )
            if not claim.counterevidence:
                findings.append(
                    Finding(
                        code="missing_counterevidence",
                        severity=Severity.WARNING,
                        claim_id=claim.id,
                        message=(
                            "High-confidence claim does not record counter-evidence."
                        ),
                        remediation="Name the strongest evidence against this claim.",
                    )
                )

    for source_id in sorted(referenced_source_ids & sources.keys()):
        source = sources[source_id]
        if not source.quote:
            findings.append(
                Finding(
                    code="missing_evidence_quote",
                    severity=Severity.WARNING,
                    source_id=source.id,
                    message="Referenced source has no evidence excerpt.",
                    remediation="Record the exact supporting excerpt from the source.",
                )
            )
        age_days = (packet.as_of - source.published_at).days
        if age_days < 0:
            findings.append(
                Finding(
                    code="future_source",
                    severity=Severity.ERROR,
                    source_id=source.id,
                    message="Source was published after the packet's as-of date.",
                    remediation="Correct the date or remove look-ahead evidence.",
                )
            )
        elif age_days > policy.max_source_age_days:
            findings.append(
                Finding(
                    code="stale_source",
                    severity=Severity.WARNING,
                    source_id=source.id,
                    message=f"Source is {age_days} days old at the as-of date.",
                    remediation=(
                        "Refresh the source or explain why older evidence "
                        "remains valid."
                    ),
                )
            )
        if source.accessed_at > packet.as_of:
            findings.append(
                Finding(
                    code="look_ahead_access",
                    severity=Severity.ERROR,
                    source_id=source.id,
                    message="Source was accessed after the packet's as-of date.",
                    remediation="Use evidence available at evaluation time.",
                )
            )
        if source.accessed_at < source.published_at:
            findings.append(
                Finding(
                    code="access_before_publication",
                    severity=Severity.ERROR,
                    source_id=source.id,
                    message="Source access date precedes its publication date.",
                    remediation="Correct the source provenance dates.",
                )
            )

    unused_sources = sorted(sources.keys() - referenced_source_ids)
    for source_id in unused_sources:
        findings.append(
            Finding(
                code="unused_source",
                severity=Severity.INFO,
                source_id=source_id,
                message="Source is included but does not support any claim.",
                remediation="Link it to a claim or remove it from the packet.",
            )
        )

    findings.extend(_numeric_conflicts(packet, policy))
    return sorted(
        findings,
        key=lambda item: (
            list(Severity).index(item.severity),
            item.code,
            item.claim_id or "",
            item.source_id or "",
        ),
    )


def _numeric_conflicts(packet: ResearchPacket, policy: AuditPolicy) -> list[Finding]:
    groups: dict[tuple[str, str, str], list[tuple[str, float]]] = defaultdict(list)
    for claim in packet.claims:
        if claim.metric and claim.period and claim.unit and claim.value is not None:
            groups[(claim.metric, claim.period, claim.unit)].append(
                (claim.id, claim.value)
            )

    findings = []
    for (metric, period, unit), values in groups.items():
        if len(values) < 2:
            continue
        numeric_values = [value for _, value in values]
        scale = max(abs(value) for value in numeric_values) or 1.0
        ratio = (max(numeric_values) - min(numeric_values)) / scale
        if ratio > policy.max_numeric_conflict_ratio:
            claim_ids = ", ".join(claim_id for claim_id, _ in values)
            findings.append(
                Finding(
                    code="numeric_conflict",
                    severity=Severity.ERROR,
                    message=(
                        f"Claims {claim_ids} disagree on {metric} for {period} "
                        f"in {unit} by {ratio:.1%}."
                    ),
                    remediation=(
                        "Resolve the discrepancy or distinguish the definitions."
                    ),
                )
            )
    return findings


def _metrics(packet: ResearchPacket) -> dict[str, int | float]:
    cited_claims = sum(bool(claim.source_ids) for claim in packet.claims)
    coverage = cited_claims / len(packet.claims) if packet.claims else 0.0
    domains = {_source_domain(source.url) for source in packet.sources}
    return {
        "claim_count": len(packet.claims),
        "source_count": len(packet.sources),
        "risk_count": len(packet.risks),
        "citation_coverage": round(coverage, 3),
        "independent_domains": len(domains),
    }


def _source_domain(url: str) -> str:
    return urlparse(url).netloc.removeprefix("www.").lower()


def _packet_hash(raw: dict[str, object]) -> str:
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
