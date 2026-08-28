import json
from datetime import date
from pathlib import Path
from typing import Any

from grounded_alpha.models import Claim, ResearchPacket, Source

CLAIM_KINDS = {"estimate", "fact", "opinion"}
SOURCE_TYPES = {"earnings", "filing", "market_data", "news", "research", "other"}


class PacketValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


def load_packet(path: Path) -> tuple[dict[str, Any], ResearchPacket]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise PacketValidationError([f"invalid JSON: {error.msg}"]) from error
    except OSError as error:
        raise PacketValidationError([str(error)]) from error
    if not isinstance(raw, dict):
        raise PacketValidationError(["packet root must be a JSON object"])
    return raw, parse_packet(raw)


def parse_packet(raw: dict[str, Any]) -> ResearchPacket:
    errors: list[str] = []
    subject = _required_string(raw, "subject", errors)
    thesis = _required_string(raw, "thesis", errors)
    as_of = _required_date(raw, "as_of", errors)

    sources_raw = raw.get("sources")
    if not isinstance(sources_raw, list):
        errors.append("sources must be a list")
        sources_raw = []
    sources = tuple(
        source
        for index, item in enumerate(sources_raw)
        if (source := _parse_source(item, index, errors)) is not None
    )

    claims_raw = raw.get("claims")
    if not isinstance(claims_raw, list):
        errors.append("claims must be a list")
        claims_raw = []
    claims = tuple(
        claim
        for index, item in enumerate(claims_raw)
        if (claim := _parse_claim(item, index, errors)) is not None
    )

    risks_raw = raw.get("risks")
    if not isinstance(risks_raw, list):
        errors.append("risks must be a list")
        risks_raw = []
    risks = tuple(
        risk.strip() for risk in risks_raw if isinstance(risk, str) and risk.strip()
    )
    if len(risks) != len(risks_raw):
        errors.append("every risk must be a non-empty string")

    _check_unique_ids("source", [source.id for source in sources], errors)
    _check_unique_ids("claim", [claim.id for claim in claims], errors)
    if errors:
        raise PacketValidationError(errors)

    return ResearchPacket(
        subject=subject,
        as_of=as_of,
        thesis=thesis,
        sources=sources,
        claims=claims,
        risks=risks,
    )


def _parse_source(raw: object, index: int, errors: list[str]) -> Source | None:
    path = f"sources[{index}]"
    if not isinstance(raw, dict):
        errors.append(f"{path} must be an object")
        return None
    source_id = _required_string(raw, "id", errors, path)
    title = _required_string(raw, "title", errors, path)
    url = _required_string(raw, "url", errors, path)
    if url and not url.startswith(("https://", "http://")):
        errors.append(f"{path}.url must use http or https")
    published_at = _required_date(raw, "published_at", errors, path)
    accessed_at = _required_date(raw, "accessed_at", errors, path)
    quote = _optional_string(raw, "quote", errors, path) or ""
    source_type = _required_string(raw, "type", errors, path)
    if source_type and source_type not in SOURCE_TYPES:
        errors.append(f"{path}.type must be one of {', '.join(sorted(SOURCE_TYPES))}")
    if not all((source_id, title, url, published_at, accessed_at, source_type)):
        return None
    return Source(
        id=source_id,
        title=title,
        url=url,
        published_at=published_at,
        accessed_at=accessed_at,
        quote=quote,
        source_type=source_type,
    )


def _parse_claim(raw: object, index: int, errors: list[str]) -> Claim | None:
    path = f"claims[{index}]"
    if not isinstance(raw, dict):
        errors.append(f"{path} must be an object")
        return None
    claim_id = _required_string(raw, "id", errors, path)
    text = _required_string(raw, "text", errors, path)
    kind = _required_string(raw, "kind", errors, path)
    if kind and kind not in CLAIM_KINDS:
        errors.append(f"{path}.kind must be one of {', '.join(sorted(CLAIM_KINDS))}")

    confidence_raw = raw.get("confidence")
    if isinstance(confidence_raw, bool) or not isinstance(confidence_raw, (int, float)):
        errors.append(f"{path}.confidence must be a number between 0 and 1")
        confidence = 0.0
    else:
        confidence = float(confidence_raw)
        if not 0 <= confidence <= 1:
            errors.append(f"{path}.confidence must be between 0 and 1")

    source_ids_raw = raw.get("source_ids", [])
    if not isinstance(source_ids_raw, list) or not all(
        isinstance(item, str) and item.strip() for item in source_ids_raw
    ):
        errors.append(f"{path}.source_ids must be a list of non-empty strings")
        source_ids: tuple[str, ...] = ()
    else:
        source_ids = tuple(item.strip() for item in source_ids_raw)

    value_raw = raw.get("value")
    if value_raw is None:
        value = None
    elif isinstance(value_raw, bool) or not isinstance(value_raw, (int, float)):
        errors.append(f"{path}.value must be a number")
        value = None
    else:
        value = float(value_raw)

    if not all((claim_id, text, kind)):
        return None
    return Claim(
        id=claim_id,
        text=text,
        kind=kind,
        confidence=confidence,
        source_ids=source_ids,
        metric=_optional_string(raw, "metric", errors, path),
        value=value,
        unit=_optional_string(raw, "unit", errors, path),
        period=_optional_string(raw, "period", errors, path),
        counterevidence=_optional_string(raw, "counterevidence", errors, path),
    )


def _required_string(
    raw: dict[str, Any], key: str, errors: list[str], path: str = "packet"
) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}.{key} must be a non-empty string")
        return ""
    return value.strip()


def _optional_string(
    raw: dict[str, Any], key: str, errors: list[str], path: str
) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}.{key} must be a non-empty string when provided")
        return None
    return value.strip()


def _required_date(
    raw: dict[str, Any], key: str, errors: list[str], path: str = "packet"
) -> date | None:
    value = raw.get(key)
    if not isinstance(value, str):
        errors.append(f"{path}.{key} must be an ISO date")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{path}.{key} must be an ISO date")
        return None


def _check_unique_ids(label: str, ids: list[str], errors: list[str]) -> None:
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        errors.append(f"duplicate {label} ids: {', '.join(duplicates)}")
