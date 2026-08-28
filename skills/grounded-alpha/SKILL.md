---
name: grounded-alpha
description: Create and audit evidence-backed financial research packets. Use when an agent develops, reviews, or publishes an investment thesis, company analysis, market brief, or due-diligence report.
---

# Grounded Alpha

Use Grounded Alpha as a deterministic evidence gate before presenting financial
research. It evaluates provenance and internal consistency, not future returns.

## Workflow

1. Set an explicit `as_of` date before collecting evidence.
2. Record every source with its publication date, access date, URL, and exact
   supporting excerpt.
3. Break the thesis into individually auditable `fact`, `estimate`, or `opinion`
   claims.
4. Give numeric claims a stable metric name, value, unit, and period.
5. Calibrate confidence and record the strongest counter-evidence for every
   high-confidence claim.
6. Name at least two concrete risks that could invalidate the thesis.
7. Write the packet described in [references/packet-format.md](references/packet-format.md).
8. Run the gate:

```bash
uvx --from git+https://github.com/Apurva3509/grounded-alpha \
  grounded-alpha research-packet.json --output grounded-alpha-report.md
```

9. Fix findings by improving the research. Never fabricate citations, alter
   dates, or lower confidence solely to game the score.
10. Present the audit score, receipt hash, unresolved findings, and the standard
    disclaimer that the output is research rather than financial advice.

## Evidence rules

- Treat `as_of` as a hard information boundary.
- Prefer primary filings, official releases, and direct market data.
- Do not count mirrors of the same document as independent evidence.
- Quote the source passage that supports the claim.
- Distinguish reported facts from estimates and interpretations.
- Preserve disagreements instead of averaging them away.
- State when a needed fact is unavailable.

An audit failure is a research result. Do not suppress it.
