---
name: implement-bi-connector
description: Research the vendor BI API, implement fetch_metadata, and verify with BI tests
argument-hint: <connector-name>
disable-model-invocation: false
---

# Implement BI Connector: Research, Implement, and Test

## Arguments

`$ARGUMENTS` contains the BI connector name (required). Example: `looker`, `domo`, `oas`.

**If no connector name is provided:** List the available BI connectors under `bi_connectors/`
(excluding `_base`) and ask the user which one to implement. Do not proceed until they respond.

## Step 1: Read the scaffold

Read the following files:
- `bi_connectors/<name>/connector.py` — your implementation file
- `bi_connectors/<name>/manifest.json` — connector identity (connection_type, asset_class, credentials_schema)
- `bi_connectors/<name>/credentials.json` — credential structure
- `bi_connectors/<name>/requirements.txt` — vendor client dependencies

If `connector.py` doesn't exist, stop and tell the user to run `/create-connector <name> --bi` first.

Also read the validators for reference:
- `bi_connectors/_base/validators.py` — the cross-field rules your returned dicts must satisfy

The dict schema (`BiAsset`, `BiAssetRef`, `BiOwner`) is defined in pycarlo:
`pycarlo.features.ingestion.bi` (requires pycarlo >= 0.15.240). Read the pycarlo source or use
web search to understand the full field list.

## Step 2: Understand the asset model

Read `manifest.json` — there is no terminology block (unlike ETL): the asset's kind is per-asset
display data carried on each returned dict's `asset_type` field, not a connector-level declaration.

`asset_type` is a free-form label (e.g. Looker "dashboard"/"look", Domo "card"/"page"/"dataset",
OAS "analysis"/"workbook"). It is never validated server-side — it becomes the type chip on the
lineage node. There is no job/task/run hierarchy — BI assets are flat, and one connector may
emit several `asset_type`s.

## Step 3: Research the vendor API

Use web search to find the vendor's API documentation. You need to identify:

1. **Authentication** — how to authenticate (API key, OAuth, access token, etc.). Note token
   privilege scope: some BI vendor tokens carry broad/admin rights (e.g. Domo) — flag
   least-privilege guidance in the connector README if so.
2. **List/enumerate assets endpoint** — to populate `BiAsset` dicts (search API, catalog API, etc.)
3. **Lineage / relationship data** — BI→BI relationships (card→dataset, page⊇card) and the
   warehouse tables an asset reads (for `inputs`).
4. **DB egress (optional)** — some BI tools keep usage stats (view counts) in warehouse tables
   reachable only by a DB connection rather than an API. The agent runtime permits native
   outbound TCP DB egress; prefer a thin native Python driver (e.g. `python-oracledb` thin mode)
   over JDBC (no JDK in the base image). Read-only, parameterized queries only.

Search for:
- `<vendor-name> API documentation`
- `<vendor-name> REST API list dashboards/cards/analyses`
- `<vendor-name> lineage API`
- `<vendor-name> Python SDK`

**Prefer a vendor SDK** if one exists (check PyPI).

## Step 4: Install the vendor client library

Add the vendor's Python SDK or HTTP library to `requirements.txt`:

```
<vendor-sdk>==<version>
```

If no SDK exists, `requests` is already available — use it for raw HTTP calls.

If the vendor client needs system-level dependencies, add them to
`bi_connectors/<name>/Dockerfile.extra` and regenerate the test Dockerfile:

```bash
python scripts/generate_test_dockerfile.py
```

Rebuild the Docker image:

```bash
docker compose build
```

## Step 5: Stub credentials.json

Update `credentials.json` with the keys your connector will need:

```json
{
  "connect_args": {
    "api_key": "<your-api-key>",
    "base_url": "https://api.vendor.com"
  }
}
```

The keys in `connect_args` are whatever your `setup_connection()` method reads via
`self.credentials`.

## Step 5b: Add a credentials schema (recommended)

Add a `credentials_schema` to `manifest.json` so the agent validates self-hosted credentials at
setup time. The schema uses [cerberus](https://docs.python-cerberus.org/) format and validates
the **entire** `credentials.json` payload, so keys must be wrapped under a top-level
`connect_args` dict (it is *not* a mirror of `self.credentials`). See the "credentials schema"
section in the repo README for the exact shape.

## Step 6: Implement the connector

Edit `bi_connectors/<name>/connector.py`. The connector **subclasses** the base:

```python
from bi_connectors._base.connector import Connector as _BaseConnector


class Connector(_BaseConnector):
    def setup_connection(self): ...
    def close_connection(self): ...
    def fetch_metadata(self, limit: int, offset: int) -> list[dict]: ...
```

### `setup_connection(self)`

Initialize the vendor API client using `self.credentials`. Store the client on `self`.

### `close_connection(self)`

Clean up any API sessions or connections.

### `fetch_metadata(self, limit: int, offset: int) -> list[dict]`

Return a list of dicts following the `BiAsset` schema in `pycarlo.features.ingestion.bi`. This
is the **only** fetch method — BI assets have no run/execution pipeline, so there is no
`fetch_run_details` and no webhook.

Required dict keys per asset:
- `asset_source_id` — unique, **vendor-stable** identifier within the container. It is the
  identity seed: it MUST remain stable across renames and moves, or Monte Carlo treats the
  asset as new.
- `name` — human-readable asset name
- `asset_type` — free-form label for the asset kind (e.g. `dashboard`, `analysis`, `card`,
  `workbook`). Never validated — display text only.

Recommended keys: `description`, `asset_url`, `folder`, `owner` (`{email, name, source_id}`),
`created_time`/`last_modified_time`/`last_viewed_time` (ISO-8601 timezone-aware), `view_count`,
`is_certified`, `certification_note`, `is_archived`, `properties` (`{key, value}`), `attributes`.

**BI→BI lineage (optional):** `upstream_assets` / `downstream_assets` — lists of
`{asset_source_id, relationship_type?}` refs where `relationship_type` is one of
`CONTAINED_IN`, `DERIVES_FROM`, `REFERENCES`. Do **not** set `container_source_id` —
cross-container references are unsupported in v1 and dropped server-side.

**Table lineage (optional):** `inputs` — a list of warehouse asset-ref dicts
(`{asset_type, role: "INPUT", fully_qualified_name?/mcon?}`, at least one identifier) describing
which tables the BI asset reads. If the vendor API can't tell you which tables a dashboard reads
(e.g. it runs SQL against the warehouse directly), tell the user about **SQL query tagging** as
an alternative — see the README's query-tagging section.

**Omit None values and empty lists** from returned dicts — the agent expects sparse dicts. A
simple helper: `{k: v for k, v in d.items() if v is not None and v != []}`.

Parameters: `limit` and `offset` support pagination — return at most `limit` assets starting
from `offset`.

## Step 7: STOP — Wait for credentials

Tell the user:

> BI connector `<name>` is implemented. Next:
>
> 1. Fill in `bi_connectors/<name>/credentials.json` with your vendor API credentials
> 2. Confirm when ready to test
>
> The keys I expect:
> ```json
> {
>   "connect_args": {
>     <list the keys your setup_connection() reads>
>   }
> }
> ```

**Do not proceed until the user confirms credentials are set.**

## Step 8: Build and test — Connection

```bash
docker compose build
CONNECTOR=<name> docker compose run --rm test -m bi_connection
```

This verifies the connector module loads and `setup_connection()` succeeds with the provided
credentials. Fix and re-test before proceeding.

## Step 9: Test — Metadata

```bash
CONNECTOR=<name> docker compose run --rm test -m bi_metadata
```

This calls `fetch_metadata()` and validates it returns a non-empty list of dicts, each with
`asset_source_id`, `name`, and `asset_type`, and that all dicts pass
`validate_bi_metadata_events()`. Fix and re-test.

## Step 10: Report and suggest next step

Print a summary of what was implemented and how many assets the test discovered. Then suggest:

> BI connector `<name>` is implemented and all tests pass. Next step: run
> `/build-agent-image <name>` to build the deployable image.
