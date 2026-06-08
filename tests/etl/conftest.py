"""ETL-specific test fixtures.

Provides session-scoped fixtures for integration-testing ETL connectors.
The root conftest handles CLI options (--etl-connector), env var resolution
(ETL_CONNECTOR), and setting config._etl_mode.
"""

from __future__ import annotations

import importlib
import json
import os
from datetime import timedelta

import pytest

from tests.conftest import _resolve_etl_connector_name

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="session")
def etl_connector(request):
    """Session-scoped ETL connector instance.

    Loads the connector module, reads credentials, creates the connector,
    and calls setup_connection(). Calls close_connection() on teardown.

    Only resolved when a test actually requests this fixture — running
    unit-only tests will not trigger module or credential loading.
    """
    name = _resolve_etl_connector_name(request.config)
    if not name:
        pytest.skip("No ETL connector specified (--etl-connector or ETL_CONNECTOR)")

    module = importlib.import_module(f"etl_connectors.{name}.connector")

    creds_path = os.path.join(_PROJECT_ROOT, "etl_connectors", name, "credentials.json")
    credentials: dict = {}
    if os.path.isfile(creds_path):
        with open(creds_path) as f:
            data = json.load(f)
        credentials = data.get("connect_args", {})

    connector = module.Connector()
    connector.credentials = credentials
    connector.setup_connection()

    yield connector

    connector.close_connection()


@pytest.fixture(scope="session")
def lookback() -> timedelta:
    """Default lookback interval for ETL fetch calls.

    Returns a timedelta defaulting to 7 days (168 hours).
    Override by setting the ETL_TEST_LOOKBACK_HOURS env var to an integer
    number of hours.
    """
    hours = int(os.environ.get("ETL_TEST_LOOKBACK_HOURS", 7 * 24))
    return timedelta(hours=hours)
