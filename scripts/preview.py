#!/usr/bin/env python3
"""Preview what a BI connector will collect — before deploying the agent.

Runs the connector's ``fetch_metadata`` against its real credentials and
prints the exact dicts it would send to Monte Carlo, plus a field-coverage
rollup. Use it to sanity-check asset types, table FQNs, and lineage edges
locally instead of discovering problems after a deploy.

Usage:
    CONNECTOR=<name> python scripts/preview.py
    CONNECTOR=<name> python scripts/preview.py --raw
    CONNECTOR=<name> python scripts/preview.py --limit 5 --offset 0
    CONNECTOR=<name> docker compose run --rm preview          # via Docker

``--raw`` dumps the full asset dicts as JSON; the default is an aligned table.
"""
import argparse
import importlib
import json
import os
import sys

# The connector dirs (bi_connectors/<name>) are namespace packages — they have
# no __init__.py and import via the repo root being on sys.path (pytest does
# this via rootdir). When run as a plain script the CWD on sys.path is
# scripts/, so put the project root there explicitly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Optional fields whose presence is worth reporting as coverage. A zero count
# usually means the vendor gates that data (or the connector doesn't map it) —
# surfaced here so it's noticed now, not in Monte Carlo.
_COVERAGE_FIELDS = (
    "description",
    "asset_url",
    "folder",
    "owner",
    "created_time",
    "view_count",
    "inputs",
    "upstream_assets",
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_connector():
    """Return (name, type) for the single requested/auto-detected connector."""
    name = os.environ.get("CONNECTOR")
    kinds = {}
    for kind, base in (("dw", "connectors"), ("etl", "etl_connectors"), ("bi", "bi_connectors")):
        base = os.path.join(_ROOT, base)
        if os.path.isdir(base):
            for d in os.listdir(base):
                if not d.startswith(("_", ".")) and os.path.isdir(os.path.join(base, d)):
                    kinds[d] = kind
    if name:
        if name not in kinds:
            sys.exit(f"Connector '{name}' not found in connectors/, etl_connectors/, or bi_connectors/.")
        return name, kinds[name]
    if len(kinds) == 1:
        only = next(iter(kinds))
        return only, kinds[only]
    sys.exit("Set CONNECTOR=<name> (found: " + ", ".join(sorted(kinds)) + ")")


def _load_connector(name, kind):
    creds_path = os.path.join(_ROOT, f"{kind}_connectors", name, "credentials.json")
    if not os.path.isfile(creds_path):
        sys.exit(f"Credentials file not found: {creds_path}")
    with open(creds_path) as f:
        credentials = json.load(f).get("connect_args", {})
    module = importlib.import_module(f"{kind}_connectors.{name}.connector")
    connector = module.Connector()
    connector.credentials = credentials
    return connector


def _table(assets):
    """Render assets as an aligned table, lineage resolved to names.

    Columns: TYPE, NAME, READS (warehouse table inputs), UPSTREAM (BI assets it
    derives from). Lineage refs show the asset's name when it appears on this
    page, else its raw source id (an off-page / cross-container ref).
    """
    names = {a.get("asset_source_id"): a.get("name", "?") for a in assets}

    def reads(asset):
        fqns = [
            r.get("fully_qualified_name") or r.get("mcon") or "?"
            for r in asset.get("inputs") or []
        ]
        return ", ".join(fqns) or "—"

    def upstream(asset):
        out = []
        for r in asset.get("upstream_assets") or []:
            sid = r.get("asset_source_id", "?")
            label = names.get(sid, sid)
            rel = r.get("relationship_type")
            out.append(f"{label} ({rel})" if rel else label)
        return ", ".join(out) or "—"

    headers = ("TYPE", "NAME", "READS", "UPSTREAM")
    rows = [
        (a.get("asset_type", "?"), a.get("name", "?"), reads(a), upstream(a))
        for a in assets
    ]
    widths = [max(len(headers[i]), *(len(r[i]) for r in rows)) for i in range(len(headers))]

    def fmt(cells):
        return "  " + "  ".join(c.ljust(w) for c, w in zip(cells, widths)).rstrip()

    lines = [fmt(headers), fmt(tuple("-" * w for w in widths))]
    lines += [fmt(r) for r in rows]
    return lines


def _coverage(assets):
    """Render per-field presence as a small table, gaps surfaced first.

    Counts non-empty occurrences of each required/optional field across the
    page. Rows sort by fill rate so the fields a reader most needs to check
    (the empty and sparse ones) sit at the top.
    """
    total = len(assets)
    fields = ("asset_source_id", "name", "asset_type") + _COVERAGE_FIELDS
    counts = [
        (field, sum(1 for a in assets if a.get(field) not in (None, [], {})))
        for field in fields
    ]
    counts.sort(key=lambda fc: (fc[1], fc[0]))

    name_w = max(len("FIELD"), *(len(f) for f, _ in counts))
    have_w = max(len("PRESENT"), *(len(str(n)) for _, n in counts))

    def fmt(field, n):
        return f"  {field.ljust(name_w)}  {str(n).rjust(have_w)}/{total}"

    lines = [f"  {'FIELD'.ljust(name_w)}  {'PRESENT'.rjust(have_w)}"]
    lines.append(f"  {'-' * name_w}  {'-' * (have_w + 1 + len(str(total)))}")
    lines += [fmt(f, n) for f, n in counts]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Preview BI connector output.")
    parser.add_argument("--raw", action="store_true", help="dump full asset dicts as JSON")
    parser.add_argument("--limit", type=int, default=100, help="page size (default 100)")
    parser.add_argument("--offset", type=int, default=0, help="page offset (default 0)")
    args = parser.parse_args()

    name, kind = _resolve_connector()
    if kind != "bi":
        sys.exit(f"preview currently supports BI connectors only; '{name}' is {kind}.")

    connector = _load_connector(name, kind)
    connector.setup_connection()
    try:
        assets = connector.fetch_metadata(limit=args.limit, offset=args.offset)
    finally:
        connector.close_connection()

    if not assets:
        print(f"{name}: no assets returned (check credentials, space/tenant access, and filters).")
        return

    print(f"{name} — {len(assets)} asset(s) (limit={args.limit}, offset={args.offset})\n")
    if args.raw:
        print(json.dumps(assets, indent=2, sort_keys=True))
    else:
        print("\n".join(_table(assets)))
        print()
    print(f"coverage (fields present across {len(assets)} asset(s)):")
    print(_coverage(assets))


if __name__ == "__main__":
    main()
