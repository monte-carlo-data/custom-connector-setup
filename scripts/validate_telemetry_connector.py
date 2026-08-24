#!/usr/bin/env python3
"""Fetch one page from a telemetry connector, validate its shape, and print it.

This stands in for the synchronous call Monolith makes through the Data
Collector during an investigation: one resource, one time window, one page,
nothing stored. Run it after implementing `connector.py`, before building the
agent image, so a human (or AI) can eyeball what the agent would actually see.

    CONNECTOR=<name> RESOURCE_ID=<vendor-resource-id> \\
        docker compose run --rm --entrypoint python test \\
        scripts/validate_telemetry_connector.py

Options (environment variables):
    WINDOW_HOURS    how far back to look (default: 1)
    PAGE_SIZE       max items per page (default: 10)
    SEARCH_REGEX    optional regex filter for logs
    SEVERITY        optional comma-separated severity filter for logs
    TELEMETRY_NAMES optional comma-separated measurement names
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from telemetry_connectors._base import validate_log_page, validate_telemetry_page  # noqa: E402


def _dump(label, obj):
    print(f"\n=== {label} ===")
    print(json.dumps(obj, indent=2, sort_keys=True, default=str))


def _report(label, errors) -> bool:
    """Print validation results for one capability. Returns True when valid."""
    if not errors:
        print(f"{label}: page shape OK")
        return True
    print(f"{label}: {len(errors)} validation error(s)")
    for error in errors:
        print(f"  - [item {error.item_index}] {error.field}: {error.message}")
    return False


def _csv_env(name) -> list[str] | None:
    raw = os.environ.get(name)
    return [value.strip() for value in raw.split(",") if value.strip()] if raw else None


def main():
    name = os.environ.get("CONNECTOR") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not name:
        sys.exit("Set CONNECTOR=<name> (or pass it as the first argument).")

    resource_id = os.environ.get("RESOURCE_ID")
    if not resource_id:
        sys.exit(
            "Set RESOURCE_ID=<vendor-resource-id> — the resource whose runtime "
            "evidence you want (an ECS task ARN, a DAG id, a job source id, ...)."
        )

    connector_dir = os.path.join(REPO_ROOT, "telemetry_connectors", name)
    if not os.path.isdir(connector_dir):
        sys.exit(f"Telemetry connector not found: telemetry_connectors/{name}/")

    with open(os.path.join(connector_dir, "manifest.json")) as f:
        capabilities = json.load(f).get("capabilities", {})

    creds_path = os.path.join(connector_dir, "credentials.json")
    if not os.path.isfile(creds_path):
        example = os.path.join(connector_dir, "credentials.json.example")
        hint = (
            f"Copy telemetry_connectors/{name}/credentials.json.example to it and fill it in."
            if os.path.isfile(example)
            else "Create it with your vendor API credentials under 'connect_args'."
        )
        sys.exit(f"Credentials file not found: telemetry_connectors/{name}/credentials.json\n{hint}")
    with open(creds_path) as f:
        credentials = json.load(f).get("connect_args", {})

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=float(os.environ.get("WINDOW_HOURS", 1)))
    page_size = int(os.environ.get("PAGE_SIZE", 10))
    # Monolith generates this per logical retrieval and reuses it across retries.
    idempotency_key = str(uuid.uuid4())

    print(f"Connector:   {name}")
    print(f"Resource:    {resource_id}")
    print(f"Window:      {start_time.isoformat()} → {end_time.isoformat()}")
    print(f"Capabilities: {capabilities}")

    connector = importlib.import_module(
        f"telemetry_connectors.{name}.connector"
    ).Connector()
    connector.credentials = credentials
    connector.setup_connection()

    valid = True
    try:
        if capabilities.get("supports_logs"):
            page = connector.fetch_logs(
                resource_id=resource_id,
                start_time=start_time,
                end_time=end_time,
                search_regex=os.environ.get("SEARCH_REGEX") or None,
                severity=_csv_env("SEVERITY"),
                page_size=page_size,
                cursor=None,
                idempotency_key=idempotency_key,
            )
            _dump("fetch_logs — one page", page)
            valid &= _report("fetch_logs", validate_log_page(page))
        else:
            print("\nfetch_logs: not advertised in manifest.json — skipped")

        if capabilities.get("supports_telemetry"):
            page = connector.fetch_telemetry(
                resource_id=resource_id,
                start_time=start_time,
                end_time=end_time,
                names=_csv_env("TELEMETRY_NAMES"),
                page_size=page_size,
                cursor=None,
                idempotency_key=idempotency_key,
            )
            _dump("fetch_telemetry — one page", page)
            valid &= _report("fetch_telemetry", validate_telemetry_page(page))
        else:
            print("\nfetch_telemetry: not advertised in manifest.json — skipped")
    finally:
        connector.close_connection()

    if not valid:
        sys.exit(1)


if __name__ == "__main__":
    main()
