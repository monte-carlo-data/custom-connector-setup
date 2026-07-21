#!/usr/bin/env python3
"""Interactive setup-validation for an ETL connector.

Runs *after* a connector's ``connector.py`` is implemented and *before* the
agent image is built. Collects one job's asset and its most-recent runs from the
live vendor, then prints how they map into Monte Carlo's ETL model — using the
connector's own terminology — so a human (or AI) can confirm the mapping looks
right before shipping.

This does not replace the pytest suite; it's an inspect-and-approve gate.

Usage (inside the Docker test image, which has the connector's vendor deps):

    CONNECTOR=<name> docker compose run --rm --entrypoint python test \\
        scripts/validate_etl_connector.py --job-id <job_source_id>

Omit ``--job-id`` to list discovered jobs and be prompted (needs a TTY).

Exit codes: 0 success (including an idle job with no recent runs),
1 requested job not found, 2 load/usage error.

Note: output can contain vendor-supplied data (run URLs, error text). Secret-
looking values are masked, but don't paste output into shared/CI logs unreviewed.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from etl_connectors._base.loader import (  # noqa: E402
    ConnectorLoadError,
    build_connector,
    load_manifest,
)
from etl_connectors._base.validation import (  # noqa: E402
    collect_validation_warnings,
    find_asset,
    format_for_display,
    paginate,
    recent_runs_for_job,
)

DEFAULT_RUN_LIMIT = 5
DEFAULT_WINDOW_HOURS = 7 * 24
ETL_CONNECTORS_DIR = os.path.join(REPO_ROOT, "etl_connectors")


def _window_hours() -> int:
    """Run-collection window, mirroring the test harness's knob.

    ``ETL_VALIDATE_WINDOW_HOURS`` takes precedence, then ``ETL_TEST_WINDOW_HOURS``
    (so the two never silently diverge), then the 7-day default.
    """
    for var in ("ETL_VALIDATE_WINDOW_HOURS", "ETL_TEST_WINDOW_HOURS"):
        value = os.environ.get(var)
        if value:
            return int(value)
    return DEFAULT_WINDOW_HOURS


def _resolve_connector_name(explicit: str | None) -> str:
    """Resolve the ETL connector name from --connector, CONNECTOR, or auto-detect."""
    name = explicit or os.environ.get("CONNECTOR")
    if name:
        return name
    candidates = []
    if os.path.isdir(ETL_CONNECTORS_DIR):
        candidates = [
            d
            for d in os.listdir(ETL_CONNECTORS_DIR)
            if not d.startswith(("_", "."))
            and os.path.isdir(os.path.join(ETL_CONNECTORS_DIR, d))
        ]
    if len(candidates) == 1:
        return candidates[0]
    raise SystemExit(
        "Specify a connector with --connector <name> or CONNECTOR=<name> "
        f"(found: {', '.join(sorted(candidates)) or 'none'})."
    )


def _prompt_for_job(assets: list, job_label: str) -> str:
    """List discovered jobs and prompt for one. Requires an interactive TTY."""
    print(f"\nDiscovered {len(assets)} {job_label.lower()}(s):")
    for asset in assets:
        print(f"  {asset.get('job_source_id')}  —  {asset.get('name')}")
    return input(f"\nEnter the {job_label} job_source_id to validate: ").strip()


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate one job's asset + recent runs for an ETL connector."
    )
    parser.add_argument(
        "--connector", help="Connector name (default: $CONNECTOR or sole ETL connector)"
    )
    parser.add_argument(
        "--job-id", help="job_source_id to validate (prompted if omitted)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_RUN_LIMIT,
        help=f"Max recent runs to show (default: {DEFAULT_RUN_LIMIT})",
    )
    args = parser.parse_args(argv)

    name = _resolve_connector_name(args.connector)
    try:
        manifest = load_manifest(name)
        connector = build_connector(name)
    except ConnectorLoadError as e:
        print(str(e), file=sys.stderr)
        return 2

    terminology = manifest.get("terminology") or {}
    job_label = terminology.get("job") or "Job"

    try:
        assets = paginate(
            lambda limit, offset: connector.fetch_metadata(limit=limit, offset=offset)
        )
        print(
            f"Collected {len(assets)} {job_label.lower()}(s) from fetch_metadata.",
            file=sys.stderr,
        )

        job_id = args.job_id
        if not job_id:
            if not sys.stdin.isatty():
                print(
                    "No --job-id given and stdin is not a TTY. Re-run with "
                    "--job-id <job_source_id>.",
                    file=sys.stderr,
                )
                return 2
            job_id = _prompt_for_job(assets, job_label)

        asset = find_asset(assets, job_id)
        if asset is None:
            print(
                f"No {job_label.lower()} found with job_source_id={job_id!r}. "
                "Re-run without --job-id to list available ids.",
                file=sys.stderr,
            )
            return 1

        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(hours=_window_hours())
        run_events = paginate(
            lambda limit, offset: connector.fetch_run_details(
                window_start=window_start,
                window_end=window_end,
                limit=limit,
                offset=offset,
            )
        )
        runs = recent_runs_for_job(run_events, job_id, args.limit)

        print(format_for_display(asset, runs, terminology))

        if not runs:
            print(
                f"\nNote: 0 runs for this {job_label.lower()} in the last "
                f"{_window_hours()}h. Widen with ETL_VALIDATE_WINDOW_HOURS if expected.",
                file=sys.stderr,
            )

        warnings = collect_validation_warnings(asset, runs, manifest)
        if warnings:
            print("\n" + "=" * 60, file=sys.stderr)
            print(
                f"{len(warnings)} schema validation warning(s) — review before approving:",
                file=sys.stderr,
            )
            for w in warnings:
                print(f"  [{w.event_index}] {w.field}: {w.message}", file=sys.stderr)

        return 0
    finally:
        connector.close_connection()


if __name__ == "__main__":
    sys.exit(main())
