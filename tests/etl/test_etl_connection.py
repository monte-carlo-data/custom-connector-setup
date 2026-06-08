"""Integration test: verify ETL connector instantiation and connection setup."""

from __future__ import annotations

import pytest


@pytest.mark.etl_connection
def test_connector_instantiation(etl_connector):
    """The etl_connector fixture must produce a valid, connected Connector."""
    assert etl_connector is not None, "etl_connector fixture returned None"
    # Verify the connector has the required interface
    assert callable(getattr(etl_connector, "fetch_metadata", None)), (
        "Connector missing callable fetch_metadata method"
    )
    assert callable(getattr(etl_connector, "fetch_run_details", None)), (
        "Connector missing callable fetch_run_details method"
    )
