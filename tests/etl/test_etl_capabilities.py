"""Granular capability tests for ETL features.

Each test probes a single feature — required or optional. Optional
features use ``pytest.xfail()`` when absent so they surface in the
capability summary without failing the suite.
"""

from __future__ import annotations

import pytest

from etl_connectors._base.validators import _normalize_status

# ── Metadata capabilities ──────────────────────────────────────────


@pytest.mark.etl_metadata
@pytest.mark.etl_capability("metadata_group")
def test_metadata_group(etl_metadata_data):
    """Metadata assets include workspace/project grouping."""
    has_group = any(
        isinstance(a.get("group"), dict) and a["group"].get("source_id")
        for a in etl_metadata_data
    )
    if not has_group:
        pytest.xfail("Optional feature: metadata group not implemented")


@pytest.mark.etl_metadata
@pytest.mark.etl_capability("metadata_tasks")
def test_metadata_tasks(etl_metadata_data):
    """Metadata assets include sub-job task breakdown."""
    has_tasks = any(
        isinstance(a.get("tasks"), list) and len(a["tasks"]) > 0
        for a in etl_metadata_data
    )
    if not has_tasks:
        pytest.xfail("Optional feature: metadata tasks not implemented")


@pytest.mark.etl_metadata
@pytest.mark.etl_capability("metadata_inputs")
def test_metadata_inputs(etl_metadata_data):
    """Metadata assets include static input lineage."""
    has_inputs = any(
        isinstance(a.get("inputs"), list) and len(a["inputs"]) > 0
        for a in etl_metadata_data
    )
    if not has_inputs:
        pytest.xfail("Optional feature: metadata inputs (static lineage) not implemented")


@pytest.mark.etl_metadata
@pytest.mark.etl_capability("metadata_outputs")
def test_metadata_outputs(etl_metadata_data):
    """Metadata assets include static output lineage."""
    has_outputs = any(
        isinstance(a.get("outputs"), list) and len(a["outputs"]) > 0
        for a in etl_metadata_data
    )
    if not has_outputs:
        pytest.xfail("Optional feature: metadata outputs (static lineage) not implemented")


@pytest.mark.etl_metadata
@pytest.mark.etl_capability("metadata_schedule")
def test_metadata_schedule(etl_metadata_data):
    """Metadata assets include schedule info."""
    has_schedule = any(a.get("schedule") for a in etl_metadata_data)
    if not has_schedule:
        pytest.xfail("Optional feature: metadata schedule not implemented")


@pytest.mark.etl_metadata
@pytest.mark.etl_capability("metadata_owner")
def test_metadata_owner(etl_metadata_data):
    """Metadata assets include ownership info."""
    has_owner = any(a.get("owner") for a in etl_metadata_data)
    if not has_owner:
        pytest.xfail("Optional feature: metadata owner not implemented")


@pytest.mark.etl_metadata
@pytest.mark.etl_capability("metadata_tags")
def test_metadata_tags(etl_metadata_data):
    """Metadata assets include tags or properties."""
    has_tags = any(a.get("tags") or a.get("properties") for a in etl_metadata_data)
    if not has_tags:
        pytest.xfail("Optional feature: metadata tags/properties not implemented")


# ── Run details capabilities ───────────────────────────────────────


@pytest.mark.etl_run_details
@pytest.mark.etl_capability("run_timing")
def test_run_timing(etl_run_events_data):
    """Run events include start_time and/or end_time."""
    has_timing = any(
        e.get("start_time") or e.get("end_time") for e in etl_run_events_data
    )
    if not has_timing:
        pytest.xfail(
            "Optional feature: run timing (start_time/end_time) not implemented"
        )


@pytest.mark.etl_run_details
@pytest.mark.etl_capability("run_error")
def test_run_error(etl_run_events_data, run_status_mapping):
    """Failed/error runs include error details."""
    failed_events = [
        e
        for e in etl_run_events_data
        if _normalize_status(e.get("status", ""), run_status_mapping)
        in ("failed", "error")
    ]
    if not failed_events:
        pytest.xfail(
            "Optional feature: run error — no failed runs in sample data to verify"
        )
    has_error = any(e.get("error") for e in failed_events)
    if not has_error:
        pytest.xfail("Optional feature: run error details not implemented")


@pytest.mark.etl_run_details
@pytest.mark.etl_capability("run_task_runs")
def test_run_task_runs(etl_run_events_data):
    """Run events include task-level execution details."""
    has_task_runs = any(
        isinstance(e.get("task_runs"), list) and len(e["task_runs"]) > 0
        for e in etl_run_events_data
    )
    if not has_task_runs:
        pytest.xfail("Optional feature: run task_runs not implemented")


@pytest.mark.etl_run_details
@pytest.mark.etl_capability("run_inputs")
def test_run_inputs(etl_run_events_data):
    """Run events include runtime input lineage."""
    has_inputs = any(
        isinstance(e.get("inputs"), list) and len(e["inputs"]) > 0
        for e in etl_run_events_data
    )
    if not has_inputs:
        pytest.xfail("Optional feature: run inputs (runtime lineage) not implemented")


@pytest.mark.etl_run_details
@pytest.mark.etl_capability("run_outputs")
def test_run_outputs(etl_run_events_data):
    """Run events include runtime output lineage."""
    has_outputs = any(
        isinstance(e.get("outputs"), list) and len(e["outputs"]) > 0
        for e in etl_run_events_data
    )
    if not has_outputs:
        pytest.xfail("Optional feature: run outputs (runtime lineage) not implemented")


@pytest.mark.etl_run_details
@pytest.mark.etl_capability("run_group")
def test_run_group(etl_run_events_data):
    """Run events include group attribution."""
    has_group = any(
        isinstance(e.get("group"), dict) and e["group"].get("source_id")
        for e in etl_run_events_data
    )
    if not has_group:
        pytest.xfail("Optional feature: run group attribution not implemented")


# ── Webhook mode ───────────────────────────────────────────────────


@pytest.mark.etl_run_details
@pytest.mark.etl_capability("run_webhook_mode")
def test_run_webhook_mode(etl_connector, etl_run_events_data):
    """fetch_run_details supports webhook mode (run_ids parameter)."""
    if not etl_run_events_data:
        pytest.xfail("No run events available to test webhook mode")
    run_ids = [
        e.get("run_source_id")
        for e in etl_run_events_data[:3]
        if e.get("run_source_id")
    ]
    if not run_ids:
        pytest.xfail("No run_source_id in polling results to test webhook mode")
    detail_events = etl_connector.fetch_run_details(run_ids=run_ids)
    assert len(detail_events) > 0, (
        "Webhook mode returned no events for run_ids: " + ", ".join(run_ids)
    )


# ── Manifest capabilities ──────────────────────────────────────────


@pytest.mark.etl_connection
@pytest.mark.etl_capability("manifest_run_status_mapping")
def test_manifest_run_status_mapping(run_status_mapping):
    """Manifest includes run_status_mapping."""
    assert run_status_mapping and isinstance(run_status_mapping, dict), (
        "run_status_mapping is required in manifest.json"
    )


@pytest.mark.etl_connection
@pytest.mark.etl_capability("manifest_task_status_mapping")
def test_manifest_task_run_status_mapping(etl_manifest):
    """Manifest includes a separate task_run_status_mapping."""
    mapping = etl_manifest.get("task_run_status_mapping")
    if not isinstance(mapping, dict) or not mapping:
        pytest.xfail(
            "Optional feature: task_run_status_mapping not declared in manifest.json"
        )


@pytest.mark.etl_connection
@pytest.mark.etl_capability("manifest_credentials_schema")
def test_manifest_credentials_schema(etl_manifest):
    """Manifest includes a credentials_schema for validation."""
    schema = etl_manifest.get("credentials_schema")
    if not isinstance(schema, dict) or not schema:
        pytest.xfail(
            "Optional feature: credentials_schema not declared in manifest.json"
        )
    # The schema validates the whole credentials.json payload, which is wrapped
    # in connect_args — so a declared schema must nest its keys under it.
    assert "connect_args" in schema, (
        "credentials_schema must wrap its keys under a top-level 'connect_args' "
        "dict — it validates the entire credentials.json payload, not the "
        "unwrapped self.credentials. See README §5b."
    )
