"""ETL-specific test fixtures.

Provides session-scoped fixtures for integration-testing ETL connectors.
The root conftest resolves the connector name and type, storing results
on config._connector_name and config._connector_type.
"""

from __future__ import annotations

import importlib
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="session")
def etl_connector(request):
    """Session-scoped ETL connector instance."""
    if getattr(request.config, "_connector_type", None) != "etl":
        pytest.skip("Not an ETL connector")

    name = request.config._connector_name
    module = importlib.import_module(f"etl_connectors.{name}.connector")

    creds_path = os.path.join(_PROJECT_ROOT, "etl_connectors", name, "credentials.json")
    if not os.path.isfile(creds_path):
        pytest.fail(
            f"Credentials file not found: {creds_path}\n"
            f"Create etl_connectors/{name}/credentials.json with your vendor API credentials."
        )
    with open(creds_path) as f:
        data = json.load(f)
    credentials = data.get("connect_args", {})

    connector = module.Connector()
    connector.credentials = credentials
    connector.setup_connection()

    yield connector

    connector.close_connection()


@pytest.fixture(scope="session")
def etl_manifest(request) -> dict:
    """Session-scoped ETL connector manifest.json contents."""
    if getattr(request.config, "_connector_type", None) != "etl":
        pytest.skip("Not an ETL connector")

    name = request.config._connector_name
    manifest_path = os.path.join(_PROJECT_ROOT, "etl_connectors", name, "manifest.json")
    if not os.path.isfile(manifest_path):
        pytest.fail(f"Manifest file not found: {manifest_path}")
    with open(manifest_path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def run_status_mapping(etl_manifest) -> dict[str, str] | None:
    """run_status_mapping from the connector's manifest, or None."""
    mapping = etl_manifest.get("run_status_mapping")
    return mapping if isinstance(mapping, dict) else None


@pytest.fixture(scope="session")
def task_run_status_mapping(etl_manifest, run_status_mapping) -> dict[str, str] | None:
    """task_run_status_mapping from the connector's manifest, falling back to run_status_mapping."""
    mapping = etl_manifest.get("task_run_status_mapping")
    if isinstance(mapping, dict):
        return mapping
    return run_status_mapping


@pytest.fixture(scope="session")
def window_end() -> datetime:
    """Upper bound (exclusive) of the run-collection window for ETL fetch calls."""
    return datetime.now(timezone.utc)


@pytest.fixture(scope="session")
def window_start(window_end) -> datetime:
    """Lower bound (inclusive) of the run-collection window for ETL fetch calls."""
    hours = int(os.environ.get("ETL_TEST_WINDOW_HOURS", 7 * 24))
    return window_end - timedelta(hours=hours)


@pytest.fixture(scope="session")
def etl_metadata_data(etl_connector):
    """Cached metadata from fetch_metadata — shared across tests."""
    return etl_connector.fetch_metadata(limit=100, offset=0)


@pytest.fixture(scope="session")
def etl_run_events_data(etl_connector, window_start, window_end):
    """Cached run events from fetch_run_details (polling mode) — shared across tests."""
    return etl_connector.fetch_run_details(
        window_start=window_start, window_end=window_end, limit=100, offset=0
    )
