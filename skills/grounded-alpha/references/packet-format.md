# Research packet format

The root JSON object requires `subject`, `as_of`, `thesis`, `sources`, `claims`,
and `risks`.

## Source fields

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable identifier referenced by claims |
| `title` | string | Human-readable source title |
| `url` | HTTP(S) URL | Original source location |
| `published_at` | ISO date | Date the evidence became public |
| `accessed_at` | ISO date | Date the researcher retrieved it |
| `quote` | string | Exact excerpt supporting a claim |
| `type` | string | `filing`, `earnings`, `market_data`, `research`, `news`, or `other` |

## Claim fields

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable claim identifier |
| `text` | string | One falsifiable statement |
| `kind` | string | `fact`, `estimate`, or `opinion` |
| `confidence` | number | Calibrated value between 0 and 1 |
| `source_ids` | string array | Evidence supporting the claim |
| `counterevidence` | string | Strongest known challenge to the claim |
| `metric` | string | Stable name for a numeric measure |
| `value` | number | Unformatted numeric value |
| `unit` | string | Unit shared by comparable values |
| `period` | string | Period shared by comparable values |

`metric`, `value`, `unit`, and `period` should be provided together. Opinion
claims may have no sources, but facts and estimates require them.
