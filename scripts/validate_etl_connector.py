#!/usr/bin/env python3
"""Fetch one asset and one recent run from an ETL connector and print them as JSON.

Run after implementing `connector.py`, before building the agent image, so a
human (or AI) can eyeball how the connector maps the vendor's data into Monte
Carlo's ETL model.

    CONNECTOR=<name> docker compose run --rm --entrypoint python test \\
        scripts/validate_etl_connector.py
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _dump(label, obj):
    print(f"\n=== {label} ===")
    print(json.dumps(obj, indent=2, sort_keys=True, default=str))


def main():
    name = os.environ.get("CONNECTOR") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not name:
        sys.exit("Set CONNECTOR=<name> (or pass it as the first argument).")

    creds_path = os.path.join(REPO_ROOT, "etl_connectors", name, "credentials.json")
    with open(creds_path) as f:
        credentials = json.load(f).get("connect_args", {})

    connector = importlib.import_module(f"etl_connectors.{name}.connector").Connector()
    connector.credentials = credentials
    connector.setup_connection()
    try:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(hours=1)

        assets = connector.fetch_metadata(limit=1, offset=0)
        runs = connector.fetch_run_details(
            window_start=window_start, window_end=window_end, limit=1, offset=0
        )

        _dump("fetch_metadata — 1 asset", assets[0] if assets else None)
        _dump("fetch_run_details — 1 run (last 1h)", runs[0] if runs else None)
    finally:
        connector.close_connection()


if __name__ == "__main__":
    main()
