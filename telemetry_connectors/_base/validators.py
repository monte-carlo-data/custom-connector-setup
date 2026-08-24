from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

MAX_ERRORS = 50


@dataclass
class ValidationError:
    """A single validation error found in a page or item."""

    field: str
    message: str
    item_index: str


def _parse_iso8601(value, field_name: str, index: str) -> list[ValidationError]:
    """Check that *value* is a timezone-aware ISO 8601 datetime string."""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return [ValidationError(field_name, f"Invalid ISO 8601 datetime: {value!r}", index)]
    if parsed.tzinfo is None:
        return [
            ValidationError(
                field_name, f"Datetime must be timezone-aware (got naive): {value!r}", index
            )
        ]
    return []


def _validate_page(page, errors: list[ValidationError]) -> list[dict]:
    """Validate the shared page envelope. Returns the items to check further."""
    if not isinstance(page, dict):
        errors.append(ValidationError("page", "page must be a dict", "page"))
        return []

    items = page.get("items")
    if items is None:
        errors.append(ValidationError("items", "items is required (use [] for no results)", "page"))
        return []
    if not isinstance(items, list):
        errors.append(ValidationError("items", "items must be a list", "page"))
        return []

    cursor = page.get("next_cursor")
    if cursor is not None and not isinstance(cursor, str):
        errors.append(
            ValidationError("next_cursor", "next_cursor must be a string or None", "page")
        )

    return items


def _validate_ascending(
    items: list[dict], errors: list[ValidationError]
) -> None:
    """Check that items are ordered by timestamp ascending.

    Bails out on any unparseable or naive timestamp — those are reported as
    their own errors, and mixing naive and aware values here would raise.
    """
    timestamps = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            parsed = datetime.fromisoformat(str(item.get("timestamp")).replace("Z", "+00:00"))
        except (ValueError, AttributeError, TypeError):
            return
        if parsed.tzinfo is None:
            return
        timestamps.append(parsed)
    if any(later < earlier for earlier, later in zip(timestamps, timestamps[1:])):
        errors.append(
            ValidationError(
                "timestamp", "items must be ordered by timestamp ascending", "page"
            )
        )


def validate_log_page(page) -> list[ValidationError]:
    """Validate a page returned by ``fetch_logs``.

    Checks:
    - the page envelope has ``items`` (list) and a string-or-None ``next_cursor``
    - each item has a timezone-aware ISO 8601 ``timestamp`` and a ``message``
    - ``severity`` is a string when present
    - items are ordered by ``timestamp`` ascending

    Returns a list of ValidationError. Empty list means the page is valid.
    """
    errors: list[ValidationError] = []
    items = _validate_page(page, errors)

    for i, item in enumerate(items):
        if len(errors) >= MAX_ERRORS:
            break
        index = str(i)
        if not isinstance(item, dict):
            errors.append(ValidationError("items", f"item at index {i} must be a dict", index))
            continue

        if item.get("timestamp"):
            errors.extend(_parse_iso8601(item["timestamp"], "timestamp", index))
        else:
            errors.append(ValidationError("timestamp", "timestamp is required", index))

        if not isinstance(item.get("message"), str):
            errors.append(ValidationError("message", "message is required and must be a string", index))

        severity = item.get("severity")
        if severity is not None and not isinstance(severity, str):
            errors.append(ValidationError("severity", "severity must be a string or None", index))

    _validate_ascending(items, errors)
    return errors[:MAX_ERRORS]


def validate_telemetry_page(page) -> list[ValidationError]:
    """Validate a page returned by ``fetch_telemetry``.

    Checks:
    - the page envelope has ``items`` (list) and a string-or-None ``next_cursor``
    - each item has a timezone-aware ISO 8601 ``timestamp``, a ``name``, and a
      ``value``
    - ``attributes`` is a dict when present
    - items are ordered by ``timestamp`` ascending

    Returns a list of ValidationError. Empty list means the page is valid.
    """
    errors: list[ValidationError] = []
    items = _validate_page(page, errors)

    for i, item in enumerate(items):
        if len(errors) >= MAX_ERRORS:
            break
        index = str(i)
        if not isinstance(item, dict):
            errors.append(ValidationError("items", f"item at index {i} must be a dict", index))
            continue

        if item.get("timestamp"):
            errors.extend(_parse_iso8601(item["timestamp"], "timestamp", index))
        else:
            errors.append(ValidationError("timestamp", "timestamp is required", index))

        if not item.get("name"):
            errors.append(ValidationError("name", "name is required", index))

        if "value" not in item:
            errors.append(ValidationError("value", "value is required", index))

        attributes = item.get("attributes")
        if attributes is not None and not isinstance(attributes, dict):
            errors.append(
                ValidationError("attributes", "attributes must be a dict or None", index)
            )

    _validate_ascending(items, errors)
    return errors[:MAX_ERRORS]
