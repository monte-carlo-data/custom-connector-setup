"""Integration test: verify BI metadata fetch and validation."""

from __future__ import annotations

import pytest

from bi_connectors._base.validators import validate_bi_metadata_events


@pytest.mark.bi_metadata
def test_fetch_metadata(bi_metadata_data):
    """fetch_metadata must return a non-empty list of valid dicts."""
    assets = bi_metadata_data

    assert len(assets) > 0, (
        "No metadata returned. Ensure the test environment has BI assets."
    )

    for i, asset in enumerate(assets):
        assert isinstance(asset, dict), (
            f"Item at index {i} is {type(asset).__name__}, expected dict"
        )
        assert asset.get("asset_source_id"), (
            f"Asset dict at index {i} has empty asset_source_id"
        )
        assert asset.get("name"), (
            f"Asset dict at index {i} has empty name"
        )
        assert asset.get("asset_type"), (
            f"Asset dict at index {i} has empty asset_type"
        )

    errors = validate_bi_metadata_events(assets)
    assert errors == [], (
        f"Metadata validation produced {len(errors)} error(s): "
        + "; ".join(f"[{e.field}] {e.message}" for e in errors)
    )
