import json

from grounded_alpha.models import AuditReport


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
