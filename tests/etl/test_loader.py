"""Cred-free unit tests for etl_connectors._base.loader.

Point the loader's project root at a temp tree (monkeypatch) so we can exercise
the manifest-load and missing-file error paths without a real connector or
credentials. Run locally with:

    python -m pytest tests/etl/test_loader.py -v
"""

from __future__ import annotations

import json
import os

import pytest

from etl_connectors._base import loader
from etl_connectors._base.loader import (
    ConnectorLoadError,
    build_connector,
    load_manifest,
)


def _make_connector_dir(root, name):
    conn_dir = os.path.join(root, "etl_connectors", name)
    os.makedirs(conn_dir)
    return conn_dir


def test_load_manifest_reads_json(tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "_PROJECT_ROOT", str(tmp_path))
    conn_dir = _make_connector_dir(str(tmp_path), "acme")
    manifest = {
        "terminology": {"job": "Pipeline"},
        "run_status_mapping": {"OK": "success"},
    }
    with open(os.path.join(conn_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f)

    assert load_manifest("acme") == manifest


def test_load_manifest_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "_PROJECT_ROOT", str(tmp_path))
    _make_connector_dir(str(tmp_path), "acme")  # dir exists, manifest does not

    with pytest.raises(ConnectorLoadError, match="Manifest file not found"):
        load_manifest("acme")


def test_build_connector_missing_credentials_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "_PROJECT_ROOT", str(tmp_path))
    _make_connector_dir(str(tmp_path), "acme")  # no credentials.json

    # Fails on the credentials check before any module import is attempted.
    with pytest.raises(ConnectorLoadError, match="Credentials file not found"):
        build_connector("acme")
