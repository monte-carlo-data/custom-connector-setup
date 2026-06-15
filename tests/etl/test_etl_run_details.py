"""Integration test: verify ETL run-detail fetch and validation."""

from __future__ import annotations

import pytest

from etl_connectors._base.validators import validate_run_events


@pytest.mark.etl_run_details
def test_fetch_run_details_polling(
    etl_connector, lookback, run_status_mapping, task_run_status_mapping
):
    """fetch_run_details in polling mode must return valid run event dicts."""
    run_events = etl_connector.fetch_run_details(lookback=lookback, limit=100, offset=0)

    assert len(run_events) > 0, (
        "No run events returned in polling mode. "
        "Ensure the test environment has recent pipeline runs."
    )

    for i, event in enumerate(run_events):
        assert isinstance(event, dict), (
            f"Item at index {i} is {type(event).__name__}, expected dict"
        )

    errors = validate_run_events(
        run_events,
        run_status_mapping=run_status_mapping,
        task_run_status_mapping=task_run_status_mapping,
    )
    assert errors == [], (
        f"Run event validation produced {len(errors)} error(s): "
        + "; ".join(f"[{e.field}] {e.message}" for e in errors)
    )


@pytest.mark.etl_run_details
def test_fetch_run_details_by_id(
    etl_connector, lookback, run_status_mapping, task_run_status_mapping
):
    """fetch_run_details in webhook mode must return events for specific run IDs."""
    # First discover some run IDs via polling
    run_events = etl_connector.fetch_run_details(lookback=lookback, limit=10, offset=0)
    if len(run_events) == 0:
        pytest.skip("No runs available to test webhook mode")

    run_ids = [e.get("run_source_id") for e in run_events[:3]]
    run_ids = [rid for rid in run_ids if rid]
    if not run_ids:
        pytest.skip(
            "No run_source_id found in polling results — cannot test webhook mode"
        )
    detail_events = etl_connector.fetch_run_details(run_ids=run_ids)

    assert len(detail_events) > 0, "No run events returned for run_ids: " + ", ".join(
        run_ids
    )

    for i, event in enumerate(detail_events):
        assert isinstance(event, dict), (
            f"Item at index {i} is {type(event).__name__}, expected dict"
        )

    returned_ids = {
        e.get("run_source_id") for e in detail_events if e.get("run_source_id")
    }
    for rid in run_ids:
        assert rid in returned_ids, f"Run ID {rid} was requested but not returned"
    assert returned_ids.issubset(set(run_ids)), (
        f"Webhook mode returned unexpected run IDs: {returned_ids - set(run_ids)}"
    )

    errors = validate_run_events(
        detail_events,
        run_status_mapping=run_status_mapping,
        task_run_status_mapping=task_run_status_mapping,
    )
    assert errors == [], (
        f"Run event validation produced {len(errors)} error(s): "
        + "; ".join(f"[{e.field}] {e.message}" for e in errors)
    )
