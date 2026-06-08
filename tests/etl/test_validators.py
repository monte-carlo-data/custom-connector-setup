from __future__ import annotations

import pytest

from etl_connectors._base.validators import (
    MAX_ERRORS,
    ValidationError,
    validate_metadata_events,
    validate_run_events,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run_event(**overrides) -> dict:
    """Build a minimal valid run event dict, applying *overrides* on top."""
    defaults = {
        "job_source_id": "job-1",
        "run_source_id": "run-1",
        "status": "success",
        "event_time": "2024-06-01T12:00:00Z",
        "end_time": "2024-06-01T12:05:00Z",
    }
    defaults.update(overrides)
    return defaults


def _make_asset(**overrides) -> dict:
    """Build a minimal valid asset dict, applying *overrides* on top."""
    defaults = {
        "job_source_id": "job-1",
        "name": "my-pipeline",
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# validate_run_events
# ---------------------------------------------------------------------------


class TestValidateRunEvents:
    """Tests for validate_run_events."""

    def test_valid_run_event_passes(self):
        """1. Valid EtlRunEvent with terminal status, end_time, and valid datetimes."""
        event = _make_run_event(
            start_time="2024-06-01T12:00:00+00:00",
            end_time="2024-06-01T12:05:00Z",
        )
        errors = validate_run_events([event])
        assert errors == []

    def test_empty_event_time_fails(self):
        """2. Empty event_time produces a required-field error."""
        event = _make_run_event(event_time="", status="in_progress")
        errors = validate_run_events([event])
        assert len(errors) == 1
        assert errors[0].field == "event_time"
        assert "required" in errors[0].message
        assert errors[0].event_index == "0"

    def test_terminal_status_without_end_time_fails(self):
        """3. Terminal status without end_time produces an error."""
        event = _make_run_event(status="success", end_time=None)
        errors = validate_run_events([event])
        assert any(
            e.field == "end_time" and "Terminal status" in e.message
            for e in errors
        )

    def test_failed_status_without_error_object_fails(self):
        """4. 'failed' status without an error object produces an error."""
        event = _make_run_event(
            status="failed",
            end_time="2024-06-01T12:05:00Z",
            error=None,
        )
        errors = validate_run_events([event])
        assert any(
            e.field == "error" and "requires an error object" in e.message
            for e in errors
        )

    def test_error_status_without_error_object_fails(self):
        """4b. 'error' status without an error object also fails."""
        event = _make_run_event(
            status="error",
            end_time="2024-06-01T12:05:00Z",
            error=None,
        )
        errors = validate_run_events([event])
        assert any(
            e.field == "error" and "requires an error object" in e.message
            for e in errors
        )

    def test_invalid_datetime_format_fails(self):
        """5. A non-ISO-8601 string in event_time triggers a parse error."""
        event = _make_run_event(event_time="not-a-date")
        errors = validate_run_events([event])
        assert any(
            e.field == "event_time" and "Invalid ISO 8601" in e.message
            for e in errors
        )

    def test_max_errors_truncation(self):
        """6. Output is capped at MAX_ERRORS even when many events have errors."""
        # Each event with empty event_time produces at least 1 error.
        # Generate well over MAX_ERRORS events.
        events = [
            _make_run_event(event_time="", status="in_progress")
            for _ in range(MAX_ERRORS + 60)
        ]
        errors = validate_run_events(events)
        assert len(errors) == MAX_ERRORS

    def test_recursive_task_runs_validation(self):
        """Nested task_run errors are caught by recursive validation with composite index."""
        bad_task_run = _make_run_event(
            event_time="not-a-date",
            status="in_progress",
            end_time=None,
        )
        parent = _make_run_event(task_runs=[bad_task_run])
        errors = validate_run_events([parent])
        # The parent itself is valid; only the nested task_run should produce errors.
        event_time_errors = [
            e for e in errors
            if e.field == "event_time" and "Invalid ISO 8601" in e.message
        ]
        assert len(event_time_errors) >= 1
        # The nested task_run is at parent index "0", task_run index 0 → composite "0.0"
        assert any(e.event_index == "0.0" for e in event_time_errors)

    def test_multiple_error_types_on_single_event(self):
        """A single event can produce multiple distinct validation errors."""
        # Empty event_time + terminal status without end_time + failed without error
        event = _make_run_event(
            event_time="",
            status="failed",
            end_time=None,
            error=None,
        )
        errors = validate_run_events([event])
        fields_hit = {e.field for e in errors}
        assert "event_time" in fields_hit
        assert "end_time" in fields_hit
        assert "error" in fields_hit

    def test_empty_run_source_id_fails(self):
        """Empty run_source_id produces a required-field error."""
        event = _make_run_event(run_source_id="")
        errors = validate_run_events([event])
        assert any(e.field == "run_source_id" and "required" in e.message for e in errors)

    def test_absent_run_source_id_fails(self):
        """Absent run_source_id produces a required-field error."""
        event = _make_run_event()
        del event["run_source_id"]
        errors = validate_run_events([event])
        assert any(e.field == "run_source_id" and "required" in e.message for e in errors)

    def test_absent_event_time_fails(self):
        """Absent event_time key produces a required-field error."""
        event = _make_run_event(status="in_progress")
        del event["event_time"]
        errors = validate_run_events([event])
        assert any(e.field == "event_time" and "required" in e.message for e in errors)

    def test_empty_run_events_list_passes(self):
        """10a. An empty list returns no errors."""
        assert validate_run_events([]) == []


# ---------------------------------------------------------------------------
# validate_metadata_events
# ---------------------------------------------------------------------------


class TestValidateMetadataEvents:
    """Tests for validate_metadata_events."""

    def test_valid_asset_passes(self):
        """7. A fully valid EtlAsset produces no errors."""
        asset = _make_asset()
        errors = validate_metadata_events([asset])
        assert errors == []

    def test_empty_job_source_id_fails(self):
        """8. Empty job_source_id triggers an error."""
        asset = _make_asset(job_source_id="")
        errors = validate_metadata_events([asset])
        assert len(errors) >= 1
        assert any(
            e.field == "job_source_id" and "required" in e.message
            for e in errors
        )

    def test_absent_job_source_id_fails(self):
        """Absent job_source_id key triggers an error."""
        event = _make_asset()
        del event["job_source_id"]
        errors = validate_metadata_events([event])
        assert any(e.field == "job_source_id" and "required" in e.message for e in errors)

    def test_empty_name_fails(self):
        """9. Empty name triggers an error."""
        asset = _make_asset(name="")
        errors = validate_metadata_events([asset])
        assert any(
            e.field == "name" and "required" in e.message
            for e in errors
        )

    def test_absent_name_fails(self):
        """Absent name key triggers an error."""
        event = _make_asset()
        del event["name"]
        errors = validate_metadata_events([event])
        assert any(e.field == "name" and "required" in e.message for e in errors)

    def test_empty_metadata_events_list_passes(self):
        """10b. An empty list returns no errors."""
        assert validate_metadata_events([]) == []
