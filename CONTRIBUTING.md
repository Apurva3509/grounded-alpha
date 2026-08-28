# Contributing

Grounded Alpha welcomes focused changes that improve the reliability,
explainability, or interoperability of financial research audits.

## Development

```bash
uv venv
source .venv/bin/activate
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests -v
uv build
```

Open an issue before beginning a large schema or scoring change. Pull requests
should explain the failure mode they address and include behavior-focused tests.
Scoring changes must preserve deterministic results and document their policy
tradeoffs.

Never include proprietary research packets, paid-source excerpts, credentials,
personal financial information, or real customer data in issues or fixtures.
