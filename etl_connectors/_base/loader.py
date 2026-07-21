"""Load an ETL connector instance and its manifest by name.

Extracted so both the pytest fixtures (`tests/etl/conftest.py`) and the
standalone `scripts/validate_etl_connector.py` share one credentials contract
instead of duplicating it. The pytest layer resolves the connector *name* from
its own config machinery and passes it in explicitly; the script resolves the
name from `--connector`/`CONNECTOR`. Neither name-resolution path belongs here —
this module just turns a name into a connector + manifest.

Errors are raised as :class:`ConnectorLoadError` with a user-facing message so
callers can present them cleanly (the fixtures re-raise via ``pytest.fail``; the
script prints to stderr).
"""

from __future__ import annotations

import importlib
import json
import os

# Repo root (…/etl_connectors/_base/loader.py → three levels up). Module-level so
# tests can point it at a temp tree via monkeypatch.
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


class ConnectorLoadError(Exception):
    """A connector or its manifest/credentials could not be loaded."""


def _connector_dir(name: str) -> str:
    return os.path.join(_PROJECT_ROOT, "etl_connectors", name)


def load_manifest(name: str) -> dict:
    """Return the parsed ``manifest.json`` for the named ETL connector."""
    manifest_path = os.path.join(_connector_dir(name), "manifest.json")
    if not os.path.isfile(manifest_path):
        raise ConnectorLoadError(f"Manifest file not found: {manifest_path}")
    with open(manifest_path) as f:
        return json.load(f)


def build_connector(name: str):
    """Instantiate the named ETL connector, wire credentials, and connect.

    Reads ``etl_connectors/<name>/credentials.json`` (``connect_args``), sets it
    on the connector, and calls ``setup_connection()``. Returns the connected
    connector; the caller is responsible for ``close_connection()``.
    """
    creds_path = os.path.join(_connector_dir(name), "credentials.json")
    if not os.path.isfile(creds_path):
        raise ConnectorLoadError(
            f"Credentials file not found: {creds_path}\n"
            f"Create etl_connectors/{name}/credentials.json with your vendor API credentials."
        )
    with open(creds_path) as f:
        data = json.load(f)

    module = importlib.import_module(f"etl_connectors.{name}.connector")
    connector = module.Connector()
    connector.credentials = data.get("connect_args", {})
    connector.setup_connection()
    return connector
