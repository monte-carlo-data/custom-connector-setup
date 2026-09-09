"""Integration test: verify BI connector instantiation and connection setup."""

from __future__ import annotations

import pytest


@pytest.mark.bi_connection
def test_connector_instantiation(bi_connector):
    """The bi_connector fixture must produce a valid, connected Connector."""
    assert bi_connector is not None, "bi_connector fixture returned None"
    # Verify the connector has the required interface. BI connectors expose
    # only fetch_metadata — there is no fetch_run_details / run pipeline.
    assert callable(getattr(bi_connector, "fetch_metadata", None)), (
        "Connector missing callable fetch_metadata method"
    )
