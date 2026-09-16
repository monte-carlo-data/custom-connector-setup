"""BI-specific test fixtures.

Provides session-scoped fixtures for integration-testing BI connectors.
The root conftest resolves the connector name and type, storing results
on config._connector_name and config._connector_type.
"""

from __future__ import annotations

import importlib
import json
import os

import pytest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="session")
def bi_connector(request):
    """Session-scoped BI connector instance."""
    if getattr(request.config, "_connector_type", None) != "bi":
        pytest.skip("Not a BI connector")

    name = request.config._connector_name
    module = importlib.import_module(f"bi_connectors.{name}.connector")

    creds_path = os.path.join(_PROJECT_ROOT, "bi_connectors", name, "credentials.json")
    if not os.path.isfile(creds_path):
        pytest.fail(
            f"Credentials file not found: {creds_path}\n"
            f"Create bi_connectors/{name}/credentials.json with your vendor API credentials."
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
def bi_manifest(request) -> dict:
    """Session-scoped BI connector manifest.json contents."""
    if getattr(request.config, "_connector_type", None) != "bi":
        pytest.skip("Not a BI connector")

    name = request.config._connector_name
    manifest_path = os.path.join(_PROJECT_ROOT, "bi_connectors", name, "manifest.json")
    if not os.path.isfile(manifest_path):
        pytest.fail(f"Manifest file not found: {manifest_path}")
    with open(manifest_path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def bi_metadata_data(bi_connector):
    """Cached metadata from fetch_metadata — shared across tests."""
    return bi_connector.fetch_metadata(limit=100, offset=0)
