"""ETL-specific test fixtures.

Provides session-scoped fixtures for integration-testing ETL connectors.
The root conftest resolves the connector name and type, storing results
on config._connector_name and config._connector_type.
"""

from __future__ import annotations

import importlib
import json
import os
from datetime import timedelta

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
def run_status_mapping(etl_connector) -> dict[str, str] | None:
    """run_status_mapping from the connector class, or None."""
    return getattr(etl_connector, "run_status_mapping", None)


@pytest.fixture(scope="session")
def task_run_status_mapping(etl_connector, run_status_mapping) -> dict[str, str] | None:
    """task_run_status_mapping from the connector class, falling back to run_status_mapping."""
    mapping = getattr(etl_connector, "task_run_status_mapping", None)
    if mapping is not None:
        return mapping
    return run_status_mapping


@pytest.fixture(scope="session")
def lookback() -> timedelta:
    """Default lookback interval for ETL fetch calls."""
    hours = int(os.environ.get("ETL_TEST_LOOKBACK_HOURS", 7 * 24))
    return timedelta(hours=hours)
