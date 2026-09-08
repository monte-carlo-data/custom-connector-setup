from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pycarlo.features.ingestion.bi import BI_RELATIONSHIP_TYPE_VALUES
from pycarlo.features.ingestion.etl import (
    ASSET_REF_ASSET_TYPE_VALUES,
    ASSET_REF_ROLE_VALUES,
)

MAX_ERRORS = 50

# Maximum number of events the ingestion gateway accepts in a single batch.
MAX_BATCH_SIZE = 100

_OWNER_KEYS = frozenset({"email", "name", "source_id"})

_TIME_FIELDS = ("created_time", "last_modified_time", "last_viewed_time")


@dataclass
class ValidationError:
    """A single validation error found in an event."""
    field: str
    message: str
    event_index: str


def _parse_iso8601(value: str, field_name: str, event_index: str) -> list[ValidationError]:
    """Try to parse an ISO 8601 datetime string. Return errors if invalid."""
    try:
        # Handle Z suffix for Python < 3.11
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return [ValidationError(
            field=field_name,
            message=f"Invalid ISO 8601 datetime: {value!r}",
            event_index=event_index,
        )]
    if dt.tzinfo is None:
        return [ValidationError(
            field=field_name,
            message=f"Datetime must be timezone-aware (got naive): {value!r}",
            event_index=event_index,
        )]
    return []


def _validate_asset_refs(
    refs: list,
    field_name: str,
    expected_role: str,
    event_index: str,
    errors: list[ValidationError],
) -> None:
    """Validate a list of asset-ref dicts (inputs).

    Checks:
    - Each item is a dict
    - ``asset_type`` is one of the allowed values
    - ``role`` is one of the allowed values and matches the list context
    - At least one of ``mcon`` or ``fully_qualified_name`` is present
    """
    for ref_idx, ref in enumerate(refs):
        if len(errors) >= MAX_ERRORS:
            return
        idx = f"{event_index}.{field_name}.{ref_idx}"
        if not isinstance(ref, dict):
            errors.append(ValidationError(field_name, f"item at index {ref_idx} must be a dict", idx))
            continue
        # asset_type
        asset_type = ref.get("asset_type")
        if not asset_type:
            errors.append(ValidationError("asset_type", "asset_type is required", idx))
        elif asset_type not in ASSET_REF_ASSET_TYPE_VALUES:
            errors.append(ValidationError(
                "asset_type",
                f"asset_type must be one of {sorted(ASSET_REF_ASSET_TYPE_VALUES)}; got {asset_type!r}",
                idx,
            ))
        # role
        role = ref.get("role")
        if not role:
            errors.append(ValidationError("role", "role is required", idx))
        elif role not in ASSET_REF_ROLE_VALUES:
            errors.append(ValidationError(
                "role",
                f"role must be one of {sorted(ASSET_REF_ROLE_VALUES)}; got {role!r}",
                idx,
            ))
        elif role != expected_role:
            errors.append(ValidationError(
                "role",
                f"role in {field_name} must be {expected_role!r}; got {role!r}",
                idx,
            ))
        # identifier — at least one of mcon or fully_qualified_name
        if not ref.get("mcon") and not ref.get("fully_qualified_name"):
            errors.append(ValidationError(
                "fully_qualified_name",
                "at least one of mcon or fully_qualified_name is required",
                idx,
            ))


def _validate_bi_asset_refs(
    refs: list,
    field_name: str,
    event_index: str,
    errors: list[ValidationError],
) -> None:
    """Validate a list of BI asset-ref dicts (upstream_assets or downstream_assets).

    Checks:
    - The value is a list
    - Each item is a dict with a non-empty ``asset_source_id``
    - ``container_source_id`` is not set (cross-container refs unsupported in v1)
    - ``relationship_type`` (when present and not None) is a valid value
    """
    if not isinstance(refs, list):
        errors.append(ValidationError(field_name, f"{field_name} must be a list", event_index))
        return
    for ref_idx, ref in enumerate(refs):
        if len(errors) >= MAX_ERRORS:
            return
        idx = f"{event_index}.{field_name}.{ref_idx}"
        if not isinstance(ref, dict):
            errors.append(ValidationError(field_name, f"item at index {ref_idx} must be a dict", idx))
            continue
        if not ref.get("asset_source_id"):
            errors.append(ValidationError("asset_source_id", "asset_source_id is required", idx))
        if "container_source_id" in ref:
            errors.append(ValidationError(
                "container_source_id",
                "cross-container refs unsupported in v1 (dropped server-side)",
                idx,
            ))
        relationship_type = ref.get("relationship_type")
        if relationship_type is not None and relationship_type not in BI_RELATIONSHIP_TYPE_VALUES:
            errors.append(ValidationError(
                "relationship_type",
                f"relationship_type must be one of {sorted(BI_RELATIONSHIP_TYPE_VALUES)}; got {relationship_type!r}",
                idx,
            ))


def validate_bi_metadata_events(events: list[dict]) -> list[ValidationError]:
    """Validate a list of BI asset dicts for cross-field consistency.

    These checks complement the ingestion gateway's Cerberus schema (which
    enforces the per-field shape). The schema source is the pycarlo BI
    models in ``pycarlo.features.ingestion.bi`` (``BiAsset``, ``BiAssetRef``,
    ``BiOwner``); the warehouse ``inputs`` reuse the shared ETL ``AssetRef``.

    Checks:
    - ``events`` is a non-empty list of at most 100 items
    - ``asset_source_id``, ``name``, ``asset_type`` are present and non-empty
    - ``owner`` (when present) is a dict whose keys are within
      {email, name, source_id}
    - ``created_time`` / ``last_modified_time`` / ``last_viewed_time`` (when
      present) are valid timezone-aware ISO 8601 datetimes
    - ``view_count`` (when present) is a non-negative int (not bool)
    - ``is_certified`` / ``is_archived`` (when present) are bools
    - ``upstream_assets`` / ``downstream_assets`` (when present) are lists of
      BI asset refs with a non-empty ``asset_source_id``, no
      ``container_source_id``, and a valid ``relationship_type``
    - ``inputs`` asset refs have valid ``asset_type``, ``role`` (INPUT), and
      at least one identifier
    - ``properties`` (when present) is a list of dicts each with a non-empty
      ``key``
    - ``attributes`` (when present) is a dict

    Returns list of ValidationError. Empty list means all events are valid.
    Stops collecting after MAX_ERRORS to avoid unbounded output.
    """
    errors: list[ValidationError] = []

    # Batch shape
    if not isinstance(events, list) or not events:
        errors.append(ValidationError("events", "events must be a non-empty list", "batch"))
        return errors[:MAX_ERRORS]
    if len(events) > MAX_BATCH_SIZE:
        errors.append(ValidationError(
            "events",
            f"batch exceeds {MAX_BATCH_SIZE} items (got {len(events)})",
            "batch",
        ))

    for i, event in enumerate(events):
        if len(errors) >= MAX_ERRORS:
            break
        idx = str(i)
        if not isinstance(event, dict):
            errors.append(ValidationError("event", f"event at index {i} must be a dict", idx))
            continue

        # Required fields
        if not event.get("asset_source_id"):
            errors.append(ValidationError("asset_source_id", "asset_source_id is required", idx))
        if not event.get("name"):
            errors.append(ValidationError("name", "name is required", idx))
        if not event.get("asset_type"):
            errors.append(ValidationError("asset_type", "asset_type is required", idx))

        # owner: if present, must be a dict with keys within {email, name, source_id}
        owner = event.get("owner")
        if owner is not None:
            if not isinstance(owner, dict):
                errors.append(ValidationError("owner", "owner must be a dict", idx))
            else:
                unexpected = set(owner) - _OWNER_KEYS
                if unexpected:
                    errors.append(ValidationError(
                        "owner",
                        f"owner keys must be within {sorted(_OWNER_KEYS)}; got unexpected {sorted(unexpected)}",
                        idx,
                    ))

        # Time fields: validate format if present
        for time_field in _TIME_FIELDS:
            value = event.get(time_field)
            if value:
                errors.extend(_parse_iso8601(value, time_field, idx))

        # view_count: if present, must be a non-negative int (not bool)
        view_count = event.get("view_count")
        if view_count is not None:
            if isinstance(view_count, bool) or not isinstance(view_count, int):
                errors.append(ValidationError("view_count", "view_count must be an int", idx))
            elif view_count < 0:
                errors.append(ValidationError("view_count", "view_count must be >= 0", idx))

        # Boolean flags
        for bool_field in ("is_certified", "is_archived"):
            value = event.get(bool_field)
            if value is not None and not isinstance(value, bool):
                errors.append(ValidationError(bool_field, f"{bool_field} must be a bool", idx))

        # BI-to-BI lineage refs
        for ref_field in ("upstream_assets", "downstream_assets"):
            refs = event.get(ref_field)
            if refs is not None:
                _validate_bi_asset_refs(refs, ref_field, idx, errors)

        # Table lineage (warehouse inputs)
        inputs = event.get("inputs")
        if inputs is not None:
            _validate_asset_refs(inputs, "inputs", "INPUT", idx, errors)

        # properties: if present, list of dicts each with a non-empty key
        properties = event.get("properties")
        if properties is not None:
            if not isinstance(properties, list):
                errors.append(ValidationError("properties", "properties must be a list", idx))
            else:
                for p_idx, prop in enumerate(properties):
                    if len(errors) >= MAX_ERRORS:
                        break
                    p_index = f"{idx}.properties.{p_idx}"
                    if not isinstance(prop, dict):
                        errors.append(ValidationError(
                            "properties", f"item at index {p_idx} must be a dict", p_index))
                        continue
                    if not prop.get("key"):
                        errors.append(ValidationError("key", "property key is required", p_index))

        # attributes: if present, must be a dict
        attributes = event.get("attributes")
        if attributes is not None and not isinstance(attributes, dict):
            errors.append(ValidationError("attributes", "attributes must be a dict", idx))

    return errors[:MAX_ERRORS]
