from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pycarlo.features.ingestion.etl import (
    ASSET_REF_ASSET_TYPE_VALUES,
    ASSET_REF_ROLE_VALUES,
)

MAX_ERRORS = 50

_TERMINAL_STATUSES = frozenset(
    {
        "success",
        "failed",
        "skipped",
        "cancelled",
        "error",
        "timed_out",
        "pass",
        "fail",
        "partial_success",
    }
)


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
    """Validate a list of asset-ref dicts (inputs or outputs).

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


def validate_run_events(events: list[dict]) -> list[ValidationError]:
    """Validate a list of run-event dicts for cross-field consistency.

    Checks:
    - event_time is valid ISO 8601
    - start_time is valid ISO 8601 when present
    - end_time is valid ISO 8601 when present
    - Terminal statuses require end_time
    - failed/error statuses require an error object
    - inputs/outputs asset refs have valid asset_type, role, and identifier
    - Recursively validates nested task_runs

    Returns list of ValidationError. Empty list means all events are valid.
    Stops collecting after MAX_ERRORS to avoid unbounded output.
    """
    errors: list[ValidationError] = []

    def _validate_run(event: dict, index: str) -> None:
        if len(errors) >= MAX_ERRORS:
            return

        # event_time must be valid ISO 8601
        event_time = event.get("event_time")
        if event_time:
            errors.extend(_parse_iso8601(event_time, "event_time", index))
        else:
            errors.append(ValidationError("event_time", "event_time is required", index))

        # run_source_id must be present and non-empty
        if not event.get("run_source_id"):
            errors.append(ValidationError("run_source_id", "run_source_id is required", index))

        # job_source_id must be present and non-empty
        if not event.get("job_source_id"):
            errors.append(ValidationError("job_source_id", "job_source_id is required", index))

        # start_time: validate format if present
        start_time = event.get("start_time")
        if start_time:
            errors.extend(_parse_iso8601(start_time, "start_time", index))

        # end_time: validate format if present
        end_time = event.get("end_time")
        if end_time:
            errors.extend(_parse_iso8601(end_time, "end_time", index))

        # Terminal status requires end_time
        status = event.get("status", "")
        status_lower = status.lower()
        if status_lower in _TERMINAL_STATUSES and not end_time:
            errors.append(ValidationError(
                "end_time",
                f"Terminal status '{status}' requires end_time",
                index,
            ))

        # failed/error status requires error object
        if status_lower in ("failed", "error") and event.get("error") is None:
            errors.append(ValidationError(
                "error",
                f"Status '{status}' requires an error object",
                index,
            ))

        # Validate inputs/outputs asset refs
        inputs = event.get("inputs", [])
        if inputs:
            _validate_asset_refs(inputs, "inputs", "INPUT", index, errors)
        outputs = event.get("outputs", [])
        if outputs:
            _validate_asset_refs(outputs, "outputs", "OUTPUT", index, errors)

        # Recursively validate task_runs
        task_runs = event.get("task_runs", [])
        if task_runs:
            for task_idx, task_run in enumerate(task_runs):
                if len(errors) >= MAX_ERRORS:
                    break
                _validate_run(task_run, f"{index}.{task_idx}")

    for i, event in enumerate(events):
        if len(errors) >= MAX_ERRORS:
            break
        _validate_run(event, str(i))

    return errors[:MAX_ERRORS]


def validate_metadata_events(events: list[dict]) -> list[ValidationError]:
    """Validate a list of asset dicts.

    Checks:
    - job_source_id is present and non-empty
    - name is present and non-empty
    - group.source_id is present when group is provided
    - tasks[].task_source_id and tasks[].name are present when tasks are provided
    - inputs/outputs asset refs have valid asset_type, role, and identifier
      (checked on the asset itself and on each task)

    Returns list of ValidationError. Empty list means all events are valid.
    """
    errors: list[ValidationError] = []

    for i, event in enumerate(events):
        if len(errors) >= MAX_ERRORS:
            break
        idx = str(i)
        if not event.get("job_source_id"):
            errors.append(ValidationError("job_source_id", "job_source_id is required", idx))
        if not event.get("name"):
            errors.append(ValidationError("name", "name is required", idx))

        # group: if present, must be a dict with source_id
        group = event.get("group")
        if group is not None:
            if not isinstance(group, dict):
                errors.append(ValidationError("group", "group must be a dict", idx))
            elif not group.get("source_id"):
                errors.append(ValidationError("group.source_id", "group.source_id is required when group is provided", idx))

        # tasks: if present, each must have task_source_id and name
        tasks = event.get("tasks")
        if tasks:
            for t_idx, task in enumerate(tasks):
                if len(errors) >= MAX_ERRORS:
                    break
                task_index = f"{idx}.tasks.{t_idx}"
                if not isinstance(task, dict):
                    errors.append(ValidationError("tasks", f"task at index {t_idx} must be a dict", idx))
                    continue
                if not task.get("task_source_id"):
                    errors.append(ValidationError("task_source_id", "task_source_id is required", task_index))
                if not task.get("name"):
                    errors.append(ValidationError("name", "task name is required", task_index))
                # Validate task-level inputs/outputs
                task_inputs = task.get("inputs", [])
                if task_inputs:
                    _validate_asset_refs(task_inputs, "inputs", "INPUT", task_index, errors)
                task_outputs = task.get("outputs", [])
                if task_outputs:
                    _validate_asset_refs(task_outputs, "outputs", "OUTPUT", task_index, errors)

        # Validate job-level inputs/outputs
        inputs = event.get("inputs", [])
        if inputs:
            _validate_asset_refs(inputs, "inputs", "INPUT", idx, errors)
        outputs = event.get("outputs", [])
        if outputs:
            _validate_asset_refs(outputs, "outputs", "OUTPUT", idx, errors)

    return errors[:MAX_ERRORS]
