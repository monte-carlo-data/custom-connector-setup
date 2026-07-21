---
name: validate-etl-connector
description: Collect one job's asset + recent runs from an implemented ETL connector and inspect how it maps into Monte Carlo's model before building the agent image
argument-hint: <connector-name> [--job-id ID]
disable-model-invocation: false
---

# Validate ETL Connector: Inspect One Job's Mapping

This is the **inspect-and-approve gate** between `/implement-etl-connector` and
`/build-agent-image`. The ETL unit tests confirm the connector returns *well-formed*
dicts; they can't confirm the connector mapped the *right* vendor concepts onto Monte
Carlo's job/task/group model (most fields are optional, so a plausible-but-wrong mapping
still passes). This step collects one real job and shows exactly how it's mapped, using
the connector's own terminology, so a human can eyeball it before shipping.

It does not replace the unit tests — run it after they pass.

## Arguments

`$ARGUMENTS` contains the ETL connector name (required) and an optional `--job-id ID`.

**If no connector name is provided:** list the ETL connectors under `etl_connectors/`
(excluding `_base`) and ask which one. Do not proceed until they respond.

## Step 1: Preconditions

Confirm the connector is implemented and its unit tests pass:
- `etl_connectors/<name>/connector.py` exists with `fetch_metadata`/`fetch_run_details` implemented
- `etl_connectors/<name>/credentials.json` has real vendor credentials
- The ETL tests pass (`/implement-etl-connector` Step 8–10). If they haven't been run, run them first — there's no point validating output the tests would reject.

## Step 2: Pick a Job ID

The script validates **one job**. The Job ID is the connector's own `job_source_id` — the
value `fetch_metadata()` returns for the pipeline/workflow/DAG you want to inspect (often a
UUID, a name, or `<workspace>:<pipeline>`).

- **If `--job-id` was provided**, use it.
- **If you (the AI) implemented `connector.py`**, you know what `job_source_id` is built from —
  tell the user what to expect and pick a representative one (prefer a job you know has recent
  runs, ideally one with a failure so error/task-run rendering is exercised).
- **Otherwise**, run the script *without* `--job-id` — it lists every discovered job (id + name)
  and prompts for a choice. This is the "how do I find the Job ID" path.

## Step 3: Run the validation script

The script must run **inside the Docker test image** (it needs the connector's vendor deps).
The image entrypoint is `pytest`, so override it with `--entrypoint python`:

```bash
CONNECTOR=<name> docker compose run --rm --entrypoint python test \
  scripts/validate_etl_connector.py --job-id <job_source_id>
```

- Omit `--job-id` to list jobs and be prompted (needs an interactive terminal — the script
  fails fast on non-TTY stdin and tells you to pass `--job-id`).
- `--limit N` controls how many recent runs are shown (default 5).
- Run window: last 7 days, override with `ETL_VALIDATE_WINDOW_HOURS` (falls back to
  `ETL_TEST_WINDOW_HOURS`). If a job is idle, the script prints the asset and a "0 runs" note
  and exits 0 — that's not a failure.

Exit codes: `0` success, `1` requested job not found, `2` load/usage error.

## Step 4: Inspect the output with the user

The output leads with a **terminology legend** mapping the connector's terms to the canonical
schema, then the job's `EtlAsset`, then its recent `EtlRunEvent`s (canonical JSON — keys are
never rewritten). Walk through it using the vendor's terms and confirm:

- **Job name** looks right — a human-readable name, not an internal identifier.
- **Tasks** (the vendor's term, e.g. Components/Nodes/Steps) are the right sub-units, and the
  hierarchy makes sense.
- **Group** (the vendor's term, e.g. Project/Workspace) is sensible — it's optional; absent is fine.
- **Optional extras** are populated where the vendor exposes them: `owner`, `trigger`, `run_url`,
  schedule, lineage `inputs`/`outputs`.
- **Schema-validation warnings**, if any, are printed as a banner — resolve them before approving.

Secret-looking values in `run_url`/`error` are masked in the output. Even so, don't paste the
output into shared or CI logs unreviewed — it contains live vendor data.

## Step 5: Approve or iterate

- **Mapping looks wrong** (wrong identifier as the name, tasks flattened, group misassigned):
  go back to `/implement-etl-connector`, fix `connector.py`, re-run the unit tests, and re-run
  this step. Do not proceed to the image.
- **Mapping looks right:** suggest the next step:

  > ETL connector `<name>` is validated — the `<job-label>` asset and recent runs map correctly.
  > Next step: run `/build-agent-image <name>` to build the deployable image.
