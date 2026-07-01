---
name: implement-etl-connector
description: Research the vendor API, implement fetch_metadata and fetch_run_details, and verify with ETL tests
argument-hint: <connector-name>
disable-model-invocation: false
---

# Implement ETL Connector: Research, Implement, and Test

## Arguments

`$ARGUMENTS` contains the ETL connector name (required). Example: `coalesce`, `talend`, `control_m`.

**If no connector name is provided:** List the available ETL connectors under `etl_connectors/`
(excluding `_base`) and ask the user which one to implement. Do not proceed until they respond.

## Step 1: Read the scaffold

Read the following files:
- `etl_connectors/<name>/connector.py` — your implementation file
- `etl_connectors/<name>/manifest.json` — connector identity and terminology
- `etl_connectors/<name>/credentials.json` — credential structure
- `etl_connectors/<name>/requirements.txt` — driver dependencies

If `connector.py` doesn't exist, stop and tell the user to run `/create-connector <name> --etl` first.

Also read the validators for reference:
- `etl_connectors/_base/validators.py` — validation rules your returned dicts must satisfy

The dict schemas (`EtlAsset`, `EtlRunEvent`, etc.) are defined in pycarlo: `pycarlo.features.ingestion.etl`. Use web search or read the pycarlo source to understand the full field list.

## Step 2: Read the terminology

Read `manifest.json` to understand the vendor's terminology mapping:

```json
{
  "terminology": { "group": "Workspace", "job": "Pipeline", "task": "Node" }
}
```

This tells you how Monte Carlo's generic concepts map to the vendor's terms. Use it to guide your API exploration — "groups" map to workspaces (or projects, environments, etc.), "jobs" map to pipelines (or workflows, DAGs, etc.), and "tasks" map to individual nodes (or steps, operators, etc.).

## Step 3: Research the vendor API

Use web search to find the vendor's API documentation. You need to identify:

1. **Authentication** — how to authenticate API calls (API key, OAuth, bearer token, etc.)
2. **List jobs/pipelines endpoint** — to populate `EtlAsset` dicts
3. **Get run history endpoint** — to populate `EtlRunEvent` dicts
4. **Get run details endpoint** — for error details, task-level breakdowns, timing

Search for:
- `<vendor-name> API documentation`
- `<vendor-name> REST API list pipelines`
- `<vendor-name> Python SDK`

**Prefer a vendor SDK** if one exists (check PyPI). SDKs are easier to use than raw HTTP and handle auth, pagination, and retries.

## Step 4: Install the vendor client library

Add the vendor's Python SDK or HTTP library to `requirements.txt`:

```
<vendor-sdk>==<version>
```

If no SDK exists, `requests` is already available — use it for raw HTTP calls.

If the vendor client needs system-level dependencies, add them to `etl_connectors/<name>/Dockerfile.extra` and regenerate the test Dockerfile:

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

The keys in `connect_args` are whatever your `setup_connection()` method reads via `self.credentials`.

## Step 6: Implement the connector

Edit `etl_connectors/<name>/connector.py`. Implement all methods:

### `setup_connection(self)`

Initialize the vendor API client using `self.credentials`. Store the client on `self` for use by other methods.

```python
def setup_connection(self):
    self.client = VendorClient(api_key=self.credentials["api_key"])
```

### `close_connection(self)`

Clean up any API sessions or connections.

### `fetch_metadata(self, limit: int, offset: int) -> list[dict]`

Return a list of dicts describing the jobs/pipelines in the vendor. Each dict should follow the `EtlAsset` schema in `pycarlo.features.ingestion.etl`. This is structural metadata only — no run history.

Required dict keys per asset:
- `job_source_id` — the vendor's unique identifier for this job
- `name` — human-readable job name

Recommended keys:
- `group` — a dict with `source_id` (required), `name`, `group_type`, `schedule`, `attributes`
- `tasks` — a list of dicts, each with `task_source_id` (required), `name` (required), `task_type`, `description`, `inputs`, `outputs`, `upstream_task_source_ids`, `triggered_job_source_ids`
- `description`, `folder`, `job_url`, `is_paused`
- `schedule` — a dict with `kind` (one of: cron, interval, event, upstream, manual) and optional `cron_expression`, `interval_seconds`, `event_trigger` (dict), etc.
- `owner` — a dict with `primary_email`, `primary_name`, etc.
- `inputs` / `outputs` — list of asset-ref dicts for lineage (connects ETL pipelines to monitored warehouse assets in Monte Carlo). Each dict needs:
  - `asset_type` — one of: `TABLE`, `VIEW`, `FILE`, `TOPIC`, `DATASET`, `DASHBOARD`
  - `role` — `INPUT` for items in the `inputs` list, `OUTPUT` for items in the `outputs` list
  - `fully_qualified_name` — vendor-native asset identifier (e.g. `"db.schema.table"`)
  - Omit `inputs`/`outputs` entirely if the vendor API doesn't expose which assets a job reads/writes. The validators will check the structure of any asset refs you do return.
  - If lineage can't be derived from the vendor API (e.g. pipelines run free-form SQL), tell the user about **SQL query tagging** as an alternative: Monte Carlo matches pipeline-identifier tags embedded in SQL (JSON comments, or Snowflake `QUERY_TAG`) ingested via warehouse query logs to create table ↔ pipeline lineage. For a custom ETL connector, tag the SQL with the same `source_id`s this connector reports — `mcd_job_id` (the asset's `job_source_id`), optionally `mcd_task_id` (a task's `task_source_id`, requires `mcd_job_id`), and `mcd_resource_id` (the connection's resource UUID) to disambiguate when the same job `source_id` exists in more than one connection. No `inputs`/`outputs` needed for the tagged queries. Note `mcd_resource_id` is assigned by Monte Carlo at integration-registration time, so it isn't available until the agent is built, registered, and the integration added — it's disambiguation-only, so the user can skip it until then. See the "Alternative: lineage via SQL query tagging" section in the repo README for the full key table and examples.

Parameters:
- `limit` and `offset` support pagination — return at most `limit` assets starting from `offset`.

### `fetch_run_details(self, run_ids=None, window_start=None, window_end=None, limit=100, offset=0) -> list[dict]`

Return a list of dicts following the `EtlRunEvent` schema in `pycarlo.features.ingestion.etl`. This method operates in **two modes**:

**Polling mode** (`window_start`/`window_end` provided, no `run_ids`): Fetch all runs that fall within the fixed `[window_start, window_end)` window — closed lower bound, open upper bound. Both bounds are timezone-aware `datetime` objects. The agent pins this window once and passes the same bounds unchanged across every paginated call, so pages never skip or duplicate runs — filter against the bounds you're given; **do not** derive the window from `now()`. `limit` and `offset` paginate results.

**Webhook mode** (`run_ids` provided): Fetch details for specific runs by ID, regardless of time window. This path is used when a webhook notifies Monte Carlo about a particular run (e.g. a failure) and we need error details, task-level breakdown, etc.

Provide `run_ids` (webhook mode) or both `window_start` and `window_end` (polling mode) — the template includes a `ValueError` guard. When `run_ids` is provided, the window is ignored.

```python
def fetch_run_details(
    self,
    run_ids: list[str] | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
```

Required dict keys per event:
- `job_source_id` — which job this run belongs to
- `run_source_id` — unique run identifier
- `status` — the vendor's raw status string (normalized via `run_status_mapping` in manifest.json)
- `event_time` — ISO 8601 timestamp

Important constraints (enforced by validators):
- **Terminal statuses** (`success`, `failed`, `error`, `cancelled`, etc.) require `end_time`
- **Failed/error statuses** require an `error` dict (with `message`, optional `code`, `failure_type`)
- All datetime fields must be valid ISO 8601

Recommended keys:
- `start_time`, `end_time` — run timing
- `trigger` — what started the run (SCHEDULE, MANUAL, API, etc.)
- `run_url` — link to the run in the vendor's UI
- `task_runs` — nested run event dicts for task-level detail
- `error` — a dict with error details for failed runs
- `inputs` / `outputs` — list of asset-ref dicts for run-level lineage (same format as `fetch_metadata` — `asset_type`, `role`, `fully_qualified_name`). Use these when lineage can vary between runs; for static lineage, populate them on the asset in `fetch_metadata` instead.

**Omit None values and empty lists** from returned dicts — the agent expects sparse dicts with only populated fields. A simple helper: `{k: v for k, v in d.items() if v is not None and v != []}`.

**Mapping vendor statuses:** The vendor's status values probably don't match `ETL_RUN_STATUS_VALUES` exactly. Add the mapping to `manifest.json` under `run_status_mapping`. The connector should return the **raw vendor status** from `fetch_run_details()`; the agent normalizes it using the manifest mapping at collection time.

```json
{
  "run_status_mapping": {
    "Succeeded": "success",
    "Failed": "failed",
    "InProgress": "in_progress",
    "Queued": "queued",
    "Cancelled": "cancelled",
    "TimedOut": "timed_out"
  }
}
```

Keys are vendor-native status strings (case-insensitive matching). Values must be members of `ETL_RUN_STATUS_VALUES`. Unmapped statuses normalize to `"unknown"` — the test framework will fail if any vendor statuses returned during testing are not covered by the mapping.

If the vendor uses **different statuses for tasks vs jobs**, add `task_run_status_mapping` as well. When absent, task runs use `run_status_mapping` as a fallback.

The test framework (`validate_run_events`) reads the mapping from `manifest.json` and normalizes statuses before checking cross-field rules (terminal status → `end_time`, failed → `error`). This means your connector can return raw vendor statuses and the validators will still work correctly.

## Step 7: STOP — Wait for credentials

Tell the user:

> ETL connector `<name>` is implemented. Next:
>
> 1. Fill in `etl_connectors/<name>/credentials.json` with your vendor API credentials
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
CONNECTOR=<name> docker compose run --rm test -m etl_connection
```

This verifies that:
- The connector module loads
- `setup_connection()` succeeds with the provided credentials

**If it fails:** Diagnose based on the error:
- `ImportError` — check `requirements.txt`, rebuild image
- `ModuleNotFoundError` — vendor SDK name mismatch
- `ConnectionError` / `AuthenticationError` — check credentials
- `KeyError` — credential key mismatch between `credentials.json` and `setup_connection()`

Fix and re-test before proceeding.

## Step 9: Test — Metadata

```bash
CONNECTOR=<name> docker compose run --rm test -m etl_metadata
```

This calls `fetch_metadata()` and validates:
- Returns a non-empty list of dicts
- Each dict has `job_source_id` and `name`
- All dicts pass `validate_metadata_events()`

**If it fails:**
- Empty results — check that the vendor account has jobs/pipelines
- Type errors — ensure you're returning dicts, not model objects
- Validation errors — check required fields

Fix and re-test.

## Step 10: Test — Run Details

```bash
CONNECTOR=<name> docker compose run --rm test -m etl_run_details
```

This runs two tests:

1. **Polling mode** — calls `fetch_run_details(window_start=..., window_end=..., limit=100, offset=0)` and validates:
   - Returns a non-empty list of dicts
   - Each dict has the required keys (`job_source_id`, `run_source_id`, `status`, `event_time`)
   - All dicts pass `validate_run_events()` — ISO 8601 timestamps, terminal statuses have `end_time`, failed/error statuses have `error` dicts

2. **Webhook mode** — uses run IDs discovered in polling mode, calls `fetch_run_details(run_ids=[...])`, and validates:
   - Returns events for the requested run IDs
   - All returned events pass validation

**Common failures:**
- Terminal status without `end_time` — make sure your status mapping is correct and you always set `end_time` for completed runs
- Invalid datetime — ensure all timestamps are ISO 8601 (e.g., `2024-01-15T10:30:00Z`)
- Failed status without error — include an `error` dict (with `message`, optional `code`, `failure_type`) for failed/error runs

Fix and re-test.

## Step 11: Review the capability summary

After the tests pass, the test framework prints an **ETL Capability Summary** showing which
features your connector implements. Review it with the user and call out any features marked
` - ` that the vendor API could support. The summary covers:

- **Metadata features** — group, tasks, inputs/outputs (lineage), schedule, owner, tags
- **Run details features** — timing, error details, task runs, runtime lineage, group, webhook mode
- **Manifest features** — run status mapping, task-level status mapping, credentials schema

Features marked ` - ` are optional — the connector works without them, but implementing them
enables richer observability in Monte Carlo.

## Step 12: Report and suggest next step

Print a summary of what was implemented:
- Which methods were implemented
- How many assets/runs the test discovered
- Highlight the capability summary results — which features are implemented and which are not

Then suggest:

> ETL connector `<name>` is implemented and all tests pass. Next step: run `/build-agent-image <name>` to build the deployable Docker image.
