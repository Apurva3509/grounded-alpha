import tomllib
from pathlib import Path

from grounded_alpha.models import AuditPolicy

POLICY_KEYS = {
    "fail_below",
    "high_confidence_threshold",
    "max_numeric_conflict_ratio",
    "max_source_age_days",
    "min_independent_sources",
    "min_risks",
}
INTEGER_KEYS = {
    "fail_below",
    "max_source_age_days",
    "min_independent_sources",
    "min_risks",
}
NUMBER_KEYS = {
    "high_confidence_threshold",
    "max_numeric_conflict_ratio",
}


def load_policy(path: Path | None) -> AuditPolicy:
    if path is None:
        return AuditPolicy()
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"could not load policy: {error}") from error
    values = raw.get("policy")
    if not isinstance(values, dict):
        raise ValueError("policy file must contain a [policy] table")
    unknown = sorted(set(values) - POLICY_KEYS)
    if unknown:
        raise ValueError(f"unknown policy settings: {', '.join(unknown)}")
    invalid_integers = sorted(
        key
        for key in INTEGER_KEYS & values.keys()
        if isinstance(values[key], bool) or not isinstance(values[key], int)
    )
    invalid_numbers = sorted(
        key
        for key in NUMBER_KEYS & values.keys()
        if isinstance(values[key], bool) or not isinstance(values[key], (int, float))
    )
    invalid_types = invalid_integers + invalid_numbers
    if invalid_types:
        raise ValueError(f"policy settings must be numeric: {', '.join(invalid_types)}")
    try:
        policy = AuditPolicy(**values)
    except TypeError as error:
        raise ValueError(f"invalid policy settings: {error}") from error
    policy.validate()
    return policy
