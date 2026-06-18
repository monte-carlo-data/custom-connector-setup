"""Integration test: verify ETL metadata fetch and validation."""

from __future__ import annotations

import pytest

from etl_connectors._base.validators import validate_metadata_events


@pytest.mark.etl_metadata
def test_fetch_metadata(etl_metadata_data):
    """fetch_metadata must return a non-empty list of valid dicts."""
    assets = etl_metadata_data

    assert len(assets) > 0, (
        "No metadata returned. Ensure the test environment has recent ETL activity."
    )

    for i, asset in enumerate(assets):
        assert isinstance(asset, dict), (
            f"Item at index {i} is {type(asset).__name__}, expected dict"
        )
        assert asset.get("job_source_id"), (
            f"Asset dict at index {i} has empty job_source_id"
        )
        assert asset.get("name"), (
            f"Asset dict at index {i} has empty name"
        )

    errors = validate_metadata_events(assets)
    assert errors == [], (
        f"Metadata validation produced {len(errors)} error(s): "
        + "; ".join(f"[{e.field}] {e.message}" for e in errors)
    )
