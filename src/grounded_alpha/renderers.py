import json
import re

from grounded_alpha import __version__
from grounded_alpha.models import AuditReport, Finding, Severity

SARIF_LEVELS = {
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "note",
}


def render_json(report: AuditReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"


def render_markdown(report: AuditReport) -> str:
    verdict = "PASS" if report.passed else "FAIL"
    lines = [
        f"# Grounded Alpha audit: {report.subject}",
        "",
        f"**{verdict} · {report.score}/100**",
        "",
        f"Receipt: `{report.packet_hash}`",
        "",
        "## Coverage",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in report.metrics.items():
        label = key.replace("_", " ").title()
        rendered = f"{value:.1%}" if key == "citation_coverage" else str(value)
        lines.append(f"| {label} | {rendered} |")

    lines.extend(["", "## Findings", ""])
    if not report.findings:
        lines.append("No policy violations found.")
    else:
        lines.extend(
            [
                "| Severity | Code | Subject | Finding |",
                "| --- | --- | --- | --- |",
            ]
        )
        for finding in report.findings:
            subject = finding.claim_id or finding.source_id or "packet"
            lines.append(
                f"| {finding.severity.value.upper()} | `{finding.code}` | "
                f"`{subject}` | {finding.message} |"
            )
    return "\n".join(lines) + "\n"


def render_sarif(report: AuditReport, artifact_uri: str, source_text: str) -> str:
    rules = {}
    results = []
    for finding in report.findings:
        rules.setdefault(
            finding.code,
            {
                "id": finding.code,
                "name": finding.code,
                "shortDescription": {"text": finding.message},
                "help": {"text": finding.remediation or finding.message},
                "defaultConfiguration": {"level": SARIF_LEVELS[finding.severity]},
            },
        )
        result = {
            "ruleId": finding.code,
            "level": SARIF_LEVELS[finding.severity],
            "message": {"text": _finding_message(finding)},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": artifact_uri},
                        "region": {"startLine": _finding_line(finding, source_text)},
                    }
                }
            ],
        }
        results.append(result)

    payload = {
        "$schema": ("https://json.schemastore.org/sarif-2.1.0.json"),
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Grounded Alpha",
                        "version": __version__,
                        "informationUri": (
                            "https://github.com/Apurva3509/grounded-alpha"
                        ),
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
                "properties": {
                    "packetHash": report.packet_hash,
                    "score": report.score,
                    "passed": report.passed,
                },
            }
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _finding_line(finding: Finding, source_text: str) -> int:
    identifier = finding.claim_id or finding.source_id
    if not identifier:
        return 1
    encoded_identifier = re.escape(json.dumps(identifier))
    pattern = re.compile(rf'"id"\s*:\s*{encoded_identifier}')
    for line_number, line in enumerate(source_text.splitlines(), start=1):
        if pattern.search(line):
            return line_number
    return 1


def _finding_message(finding: Finding) -> str:
    if not finding.remediation:
        return finding.message
    return f"{finding.message} {finding.remediation}"
