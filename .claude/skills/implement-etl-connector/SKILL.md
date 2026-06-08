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
- `group_source_id` — the workspace/project/environment this job belongs to
- `description`, `folder`, `job_url`, `is_paused`
- `schedule` — a dict with `kind` and optional `cron_expression`, `interval_seconds`, etc.
- `owner` — a dict with `primary_email`, `primary_name`, etc.
- `inputs` / `outputs` — list of dicts with `asset_type`, `role`, `fully_qualified_name`

Parameters:
- `limit` and `offset` support pagination — return at most `limit` assets starting from `offset`.

### `fetch_run_details(self, run_ids=None, lookback=None, limit=100, offset=0) -> list[dict]`

Return a list of dicts following the `EtlRunEvent` schema in `pycarlo.features.ingestion.etl`. This method operates in **two modes**:

**Polling mode** (`lookback` provided, no `run_ids`): Fetch all runs updated within the time window. The agent calls this on a schedule to discover recent activity. Compute `since = datetime.now(timezone.utc) - lookback` and return runs newer than that. `limit` and `offset` paginate results.

**Webhook mode** (`run_ids` provided): Fetch details for specific runs by ID, regardless of time window. This path is used when a webhook notifies Monte Carlo about a particular run (e.g. a failure) and we need error details, task-level breakdown, etc.

At least one of `run_ids` or `lookback` must be provided — the template includes a `ValueError` guard. When `run_ids` is provided, `lookback` is ignored.

```python
def fetch_run_details(
    self,
    run_ids: list[str] | None = None,
    lookback: timedelta | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
```

Required dict keys per event:
- `job_source_id` — which job this run belongs to
- `run_source_id` — unique run identifier
- `status` — one of the values in `ETL_RUN_STATUS_VALUES` (see `pycarlo.features.ingestion.etl`)
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
- `inputs` / `outputs` — list of dicts for run-level lineage

**Omit None values and empty lists** from returned dicts — the agent expects sparse dicts with only populated fields. A simple helper: `{k: v for k, v in d.items() if v is not None and v != []}`.

**Mapping vendor statuses:** The vendor's status values probably don't match `ETL_RUN_STATUS_VALUES` exactly. Create a mapping from vendor statuses to the allowed values. When in doubt, use `"unknown"`.

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

1. **Polling mode** — calls `fetch_run_details(lookback=..., limit=100, offset=0)` and validates:
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

## Step 11: Report and suggest next step

Print a summary of what was implemented:
- Which methods were implemented
- How many assets/runs the test discovered
- Any fields left unpopulated (with reasons)

Then suggest:

> ETL connector `<name>` is implemented and all tests pass. Next step: run `/build-agent-image <name>` to build the deployable Docker image.
