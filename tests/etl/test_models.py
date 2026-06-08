"""Tests for ETL model dataclasses (serialization, defaults, exclude logic)."""

from __future__ import annotations

import json

import pytest

from pycarlo.features.ingestion.etl import (
    AssetRef,
    EtlAsset,
    EtlError,
    EtlRunEvent,
    Owner,
    Schedule,
)
from pycarlo.features.ingestion.models import Tag


# ---------------------------------------------------------------------------
# Fixtures — reusable model instances
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_tag() -> Tag:
    return Tag(key="env", value="production")


@pytest.fixture()
def sample_asset_ref() -> AssetRef:
    return AssetRef(
        asset_type="TABLE",
        role="INPUT",
        mcon="MCON++abc123",
        fully_qualified_name="db.schema.table",
        metadata={"row_count": 1000},
    )


@pytest.fixture()
def sample_error() -> EtlError:
    return EtlError(
        message="Connection timed out",
        code="E001",
        retryable=True,
        failure_type="TRANSIENT",
        upstream_failed_task_source_ids=["task-1", "task-2"],
        structured_fields={"host": "db.example.com"},
    )


@pytest.fixture()
def sample_schedule() -> Schedule:
    return Schedule(
        kind="cron",
        cron_expression="0 * * * *",
        interval_seconds=3600,
        timezone="UTC",
        next_run_at="2026-06-05T00:00:00Z",
        paused=False,
        event_trigger="file_arrival",
        upstream_job_global_ids=["upstream-job-1"],
        raw={"source": "airflow"},
    )


@pytest.fixture()
def sample_owner() -> Owner:
    return Owner(
        primary_email="alice@example.com",
        primary_name="Alice",
        primary_external_id="ext-42",
        run_as_email="service@example.com",
        notification_emails=["ops@example.com"],
        team="data-eng",
        raw={"ldap_group": "data-team"},
    )


@pytest.fixture()
def minimal_run_event() -> EtlRunEvent:
    """EtlRunEvent with only required fields."""
    return EtlRunEvent(
        job_source_id="job-1",
        run_source_id="run-1",
        status="success",
        event_time="2026-06-04T12:00:00Z",
    )


@pytest.fixture()
def full_run_event(sample_error, sample_asset_ref, sample_tag) -> EtlRunEvent:
    """EtlRunEvent with every field populated, including nested task_runs."""
    child_run = EtlRunEvent(
        job_source_id="job-1",
        run_source_id="run-1-child",
        status="success",
        event_time="2026-06-04T12:05:00Z",
        task_source_id="task-A",
    )
    return EtlRunEvent(
        job_source_id="job-1",
        run_source_id="run-1",
        status="failed",
        event_time="2026-06-04T12:00:00Z",
        job_run_id="jr-1",
        task_source_id="task-root",
        start_time="2026-06-04T11:55:00Z",
        end_time="2026-06-04T12:00:00Z",
        expected_end_time="2026-06-04T12:30:00Z",
        queued_at="2026-06-04T11:50:00Z",
        trigger="SCHEDULE",
        triggered_by_run_source_id="run-0",
        parent_attempt_run_source_id="run-0-attempt",
        attempt_number=2,
        backfill_id="bf-1",
        error=sample_error,
        run_url="https://airflow.example.com/runs/run-1",
        task_runs=[child_run],
        inputs=[sample_asset_ref],
        outputs=[
            AssetRef(asset_type="TABLE", role="OUTPUT", fully_qualified_name="db.schema.output_table")
        ],
        properties=[sample_tag],
        attributes={"custom_key": "custom_value"},
    )


@pytest.fixture()
def full_etl_asset(sample_schedule, sample_owner, sample_tag, sample_asset_ref) -> EtlAsset:
    """EtlAsset with every field populated."""
    return EtlAsset(
        job_source_id="job-99",
        name="daily_ingest",
        group_source_id="group-1",
        description="Ingests data from source daily",
        folder="/dags/ingest",
        is_paused=False,
        job_url="https://airflow.example.com/dags/daily_ingest",
        schedule=sample_schedule,
        owner=sample_owner,
        properties=[sample_tag, Tag(key="tier", value="gold")],
        inputs=[sample_asset_ref],
        outputs=[AssetRef(asset_type="FILE", role="OUTPUT", fully_qualified_name="s3://bucket/out")],
        attributes={"retry_policy": "exponential"},
    )


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------


class TestTag:
    def test_round_trip(self, sample_tag):
        d = sample_tag.to_dict()
        restored = Tag.from_dict(d)
        assert restored == sample_tag

    def test_exclude_none_value(self):
        tag = Tag(key="flag")
        d = tag.to_dict()
        assert "value" not in d
        assert d == {"key": "flag"}

    def test_value_present_when_set(self, sample_tag):
        d = sample_tag.to_dict()
        assert d["value"] == "production"


# ---------------------------------------------------------------------------
# AssetRef
# ---------------------------------------------------------------------------


class TestAssetRef:
    def test_round_trip(self, sample_asset_ref):
        d = sample_asset_ref.to_dict()
        restored = AssetRef.from_dict(d)
        assert restored == sample_asset_ref

    def test_exclude_none_optional_fields(self):
        ref = AssetRef(asset_type="VIEW", role="OUTPUT", fully_qualified_name="db.schema.v")
        d = ref.to_dict()
        assert d["asset_type"] == "VIEW"
        assert d["role"] == "OUTPUT"
        assert "mcon" not in d
        assert "metadata" not in d

    def test_metadata_dict_preserved(self, sample_asset_ref):
        d = sample_asset_ref.to_dict()
        assert d["metadata"] == {"row_count": 1000}

    def test_invalid_asset_type_raises(self):
        with pytest.raises(ValueError, match="asset_type"):
            AssetRef(asset_type="INVALID", role="INPUT", fully_qualified_name="x")

    def test_invalid_role_raises(self):
        with pytest.raises(ValueError, match="role"):
            AssetRef(asset_type="TABLE", role="INVALID", fully_qualified_name="x")

    def test_missing_mcon_and_fqn_raises(self):
        with pytest.raises(ValueError, match="mcon or fully_qualified_name"):
            AssetRef(asset_type="TABLE", role="INPUT")


# ---------------------------------------------------------------------------
# EtlError
# ---------------------------------------------------------------------------


class TestEtlError:
    def test_round_trip(self, sample_error):
        d = sample_error.to_dict()
        restored = EtlError.from_dict(d)
        assert restored == sample_error

    def test_message_is_required(self):
        """EtlError.message is a required field — construction without it fails."""
        with pytest.raises(TypeError):
            EtlError()

    def test_minimal_error_excludes_optionals(self):
        err = EtlError(message="Something broke")
        d = err.to_dict()
        assert d == {"message": "Something broke"}

    def test_non_empty_upstream_ids_included(self, sample_error):
        d = sample_error.to_dict()
        assert d["upstream_failed_task_source_ids"] == ["task-1", "task-2"]


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------


class TestSchedule:
    def test_round_trip(self, sample_schedule):
        d = sample_schedule.to_dict()
        restored = Schedule.from_dict(d)
        assert restored == sample_schedule

    def test_minimal_schedule_excludes_optionals(self):
        sched = Schedule(kind="manual")
        d = sched.to_dict()
        assert d == {"kind": "manual"}

    def test_all_fields_present_when_set(self, sample_schedule):
        d = sample_schedule.to_dict()
        assert d["kind"] == "cron"
        assert d["cron_expression"] == "0 * * * *"
        assert d["interval_seconds"] == 3600
        assert d["timezone"] == "UTC"
        assert d["paused"] is False
        assert d["upstream_job_global_ids"] == ["upstream-job-1"]
        assert d["raw"] == {"source": "airflow"}


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------


class TestOwner:
    def test_round_trip(self, sample_owner):
        d = sample_owner.to_dict()
        restored = Owner.from_dict(d)
        assert restored == sample_owner

    def test_minimal_owner_excludes_optionals(self):
        owner = Owner()
        d = owner.to_dict()
        assert d == {}

    def test_notification_emails_excluded_when_empty(self):
        owner = Owner(primary_name="Bob")
        d = owner.to_dict()
        assert "notification_emails" not in d

    def test_notification_emails_included_when_populated(self, sample_owner):
        d = sample_owner.to_dict()
        assert d["notification_emails"] == ["ops@example.com"]


# ---------------------------------------------------------------------------
# EtlAsset
# ---------------------------------------------------------------------------


class TestEtlAsset:
    def test_from_dict_all_fields(self, full_etl_asset):
        """from_dict works with every field populated."""
        d = full_etl_asset.to_dict()
        restored = EtlAsset.from_dict(d)
        assert restored == full_etl_asset

    def test_required_fields_only(self):
        asset = EtlAsset(job_source_id="j1", name="my_job")
        assert asset.group_source_id is None
        assert asset.schedule is None
        assert asset.owner is None
        assert asset.properties == []
        assert asset.inputs == []
        assert asset.outputs == []
        assert asset.attributes is None

    def test_exclude_none_and_empty_on_minimal(self):
        asset = EtlAsset(job_source_id="j1", name="my_job")
        d = asset.to_dict()
        assert d == {"job_source_id": "j1", "name": "my_job"}

    def test_nested_schedule_and_owner(self, full_etl_asset, sample_schedule, sample_owner):
        d = full_etl_asset.to_dict()
        assert d["schedule"] == sample_schedule.to_dict()
        assert d["owner"] == sample_owner.to_dict()

    def test_nested_properties_list(self, full_etl_asset):
        d = full_etl_asset.to_dict()
        assert len(d["properties"]) == 2
        assert d["properties"][0] == {"key": "env", "value": "production"}
        assert d["properties"][1] == {"key": "tier", "value": "gold"}

    def test_nested_inputs_outputs(self, full_etl_asset, sample_asset_ref):
        d = full_etl_asset.to_dict()
        assert d["inputs"][0] == sample_asset_ref.to_dict()
        assert d["outputs"][0]["asset_type"] == "FILE"
        assert d["outputs"][0]["role"] == "OUTPUT"


# ---------------------------------------------------------------------------
# EtlRunEvent
# ---------------------------------------------------------------------------


class TestEtlRunEvent:
    def test_to_dict_round_trip(self, full_run_event):
        """Create -> to_dict -> from_dict -> compare."""
        d = full_run_event.to_dict()
        restored = EtlRunEvent.from_dict(d)
        assert restored == full_run_event

    def test_optional_fields_default_correctly(self, minimal_run_event):
        """Required-only construction sets optionals to None / empty list."""
        e = minimal_run_event
        assert e.job_run_id is None
        assert e.task_source_id is None
        assert e.start_time is None
        assert e.end_time is None
        assert e.expected_end_time is None
        assert e.queued_at is None
        assert e.trigger is None
        assert e.triggered_by_run_source_id is None
        assert e.parent_attempt_run_source_id is None
        assert e.attempt_number is None
        assert e.backfill_id is None
        assert e.error is None
        assert e.run_url is None
        assert e.task_runs == []
        assert e.inputs == []
        assert e.outputs == []
        assert e.properties == []
        assert e.attributes is None

    def test_exclude_none_fields_in_to_dict(self, minimal_run_event):
        d = minimal_run_event.to_dict()
        expected_keys = {"job_source_id", "run_source_id", "status", "event_time"}
        assert set(d.keys()) == expected_keys

    def test_exclude_empty_lists_in_to_dict(self, minimal_run_event):
        d = minimal_run_event.to_dict()
        for list_field in ("task_runs", "inputs", "outputs", "properties"):
            assert list_field not in d

    def test_nested_error_serializes(self, full_run_event, sample_error):
        d = full_run_event.to_dict()
        assert d["error"] == sample_error.to_dict()

    def test_nested_task_runs_serialize(self, full_run_event):
        d = full_run_event.to_dict()
        assert len(d["task_runs"]) == 1
        child = d["task_runs"][0]
        assert child["run_source_id"] == "run-1-child"
        assert child["task_source_id"] == "task-A"
        assert child["status"] == "success"

    def test_nested_inputs_outputs_serialize(self, full_run_event):
        d = full_run_event.to_dict()
        assert len(d["inputs"]) == 1
        assert d["inputs"][0]["asset_type"] == "TABLE"
        assert d["inputs"][0]["role"] == "INPUT"
        assert len(d["outputs"]) == 1
        assert d["outputs"][0]["role"] == "OUTPUT"

    def test_nested_properties_serialize(self, full_run_event):
        d = full_run_event.to_dict()
        assert d["properties"] == [{"key": "env", "value": "production"}]

    def test_to_json_produces_valid_json(self, full_run_event):
        """to_json() output must be parseable by json.loads."""
        json_str = full_run_event.to_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert parsed["job_source_id"] == "job-1"

    def test_to_json_minimal_produces_valid_json(self, minimal_run_event):
        json_str = minimal_run_event.to_json()
        parsed = json.loads(json_str)
        assert parsed == {
            "job_source_id": "job-1",
            "run_source_id": "run-1",
            "status": "success",
            "event_time": "2026-06-04T12:00:00Z",
        }

    def test_from_dict_round_trip_preserves_nested_task_run_children(self):
        """Verify deeply nested task_runs survive a full round-trip."""
        grandchild = EtlRunEvent(
            job_source_id="job-1",
            run_source_id="run-gc",
            status="success",
            event_time="2026-06-04T12:10:00Z",
        )
        child = EtlRunEvent(
            job_source_id="job-1",
            run_source_id="run-child",
            status="success",
            event_time="2026-06-04T12:08:00Z",
            task_runs=[grandchild],
        )
        parent = EtlRunEvent(
            job_source_id="job-1",
            run_source_id="run-parent",
            status="success",
            event_time="2026-06-04T12:00:00Z",
            task_runs=[child],
        )
        d = parent.to_dict()
        restored = EtlRunEvent.from_dict(d)
        assert restored == parent
        assert len(restored.task_runs) == 1
        assert len(restored.task_runs[0].task_runs) == 1
        assert restored.task_runs[0].task_runs[0].run_source_id == "run-gc"

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="status"):
            EtlRunEvent(
                job_source_id="job-1",
                run_source_id="run-1",
                status="INVALID_STATUS",
                event_time="2026-06-04T12:00:00Z",
            )

    def test_invalid_trigger_raises(self):
        with pytest.raises(ValueError, match="trigger"):
            EtlRunEvent(
                job_source_id="job-1",
                run_source_id="run-1",
                status="success",
                event_time="2026-06-04T12:00:00Z",
                trigger="INVALID_TRIGGER",
            )
