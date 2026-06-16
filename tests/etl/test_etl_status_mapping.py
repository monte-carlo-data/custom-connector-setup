"""Integration test: validate run_status_mapping declared on the Connector class."""

from __future__ import annotations

import pytest

from pycarlo.features.ingestion.etl import ETL_RUN_STATUS_VALUES


def _validate_mapping(mapping: dict[str, str] | None, field_name: str) -> list[str]:
    """Validate a status mapping dict. Returns a list of error strings."""
    if mapping is None:
        return []

    errors: list[str] = []
    if not isinstance(mapping, dict):
        return [f"{field_name} must be a dict or None, got {type(mapping).__name__}"]

    seen_lower_keys: dict[str, str] = {}
    for key, value in mapping.items():
        if not isinstance(key, str) or not key:
            errors.append(f"{field_name} has an empty or non-string key")
            continue
        if not isinstance(value, str):
            errors.append(
                f"{field_name} value for key '{key}' must be a string, "
                f"got {type(value).__name__}"
            )
            continue
        if value.lower() not in ETL_RUN_STATUS_VALUES:
            errors.append(
                f"{field_name} value '{value}' for key '{key}' "
                f"is not a valid ETL run status"
            )
        lower_key = key.lower()
        if lower_key in seen_lower_keys:
            errors.append(
                f"{field_name} has case-insensitive duplicate keys: "
                f"'{seen_lower_keys[lower_key]}' and '{key}'"
            )
        else:
            seen_lower_keys[lower_key] = key

    return errors


@pytest.mark.etl_connection
def test_run_status_mapping_values_are_valid(run_status_mapping):
    """All run_status_mapping values must be valid ETL_RUN_STATUS_VALUES members."""
    errors = _validate_mapping(run_status_mapping, "run_status_mapping")
    assert errors == [], "run_status_mapping validation failed:\n" + "\n".join(
        f"  - {e}" for e in errors
    )


@pytest.mark.etl_connection
def test_task_run_status_mapping_values_are_valid(
    task_run_status_mapping, run_status_mapping
):
    """All task_run_status_mapping values must be valid ETL_RUN_STATUS_VALUES members."""
    if task_run_status_mapping is run_status_mapping:
        pytest.skip(
            "task_run_status_mapping falls back to run_status_mapping (not declared separately)"
        )
    errors = _validate_mapping(task_run_status_mapping, "task_run_status_mapping")
    assert errors == [], "task_run_status_mapping validation failed:\n" + "\n".join(
        f"  - {e}" for e in errors
    )
