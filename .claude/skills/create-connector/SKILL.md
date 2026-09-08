---
name: create-connector
description: Scaffold a new connector directory with base template, manifest, credentials.json, and requirements.txt
argument-hint: <connector-name>
disable-model-invocation: true
---

# Create Connector: Scaffold a New Connector

## Arguments

`$ARGUMENTS` contains the connector name (required) and optionally `--etl` or `--bi`.

Parse `$ARGUMENTS`:
- If `--etl` is present, this is an ETL connector
- If `--bi` is present, this is a BI connector
- Everything else is the connector name
- Default is data warehouse (no flag)

Examples: `snowflake`, `bigquery`, `coalesce --etl`, `talend --etl`, `domo --bi`, `looker --bi`.

## Step 1: Run the scaffold script

**For DW connectors** (default):

```bash
python scripts/create_connector.py <connector-name>
```

This creates `connectors/<name>/` with:
- `connector.py` — base template with all stubs
- `manifest.json` — unique connector type identifier
- `credentials.json` — empty credentials template
- `requirements.txt` — empty driver file
- `Dockerfile.extra` — system dependency instructions (empty by default)

**For ETL connectors** (`--etl`):

```bash
python scripts/create_connector.py <connector-name> --etl
```

This is interactive — it prompts for terminology mappings (group/job/task labels) and an optional icon URL. **Before running the script, ask the user** for both:

1. **Terminology** — propose a mapping based on the vendor's terms (e.g., for Coalesce: job=Job, task=Node; for Azure Data Factory: job=Pipeline, task=Activity) and let the user confirm or adjust.
   - `job` and `task` are always required. **`group` is optional** — it only applies when the vendor can host the *same* job in multiple named environments (e.g. Dev and Prod) and you need to tell those instances apart. Most integrations don't have this concept — leave `group` blank unless the vendor clearly does (e.g. Matillion "Environment", a "Workspace" that duplicates jobs). When in doubt, omit it; it can be added to `manifest.json` later.
2. **Icon URL** — ask if they want a custom icon for the integration (shown in the Monte Carlo UI). Must be a publicly reachable image URL (SVG/PNG). Verify it returns HTTP 200 before using. Skip if they don't want one — it can be added later as the `icon_url` key in `manifest.json` (requires rebuilding the agent image).

Then answer the script's prompts with those values (pipe via stdin if running non-interactively).

This creates `etl_connectors/<name>/` with:
- `connector.py` — `Connector` class with `fetch_metadata` and `fetch_run_details` stubs
- `manifest.json` — connector identity with terminology mapping
- `credentials.json` — vendor API credential template (not database credentials)
- `requirements.txt` — vendor SDK dependencies

**For BI connectors** (`--bi`):

```bash
python scripts/create_connector.py <connector-name> --bi
```

This is interactive — it prompts for an optional icon URL. **Before running the script, ask the user:**

1. **Icon URL** — ask if they want a custom icon for the integration (shown in the Monte Carlo UI). Must be a publicly reachable image URL (SVG/PNG). Verify it returns HTTP 200 before using. Skip if they don't want one — it can be added later as the `icon_url` key in `manifest.json` (requires rebuilding the agent image).

Unlike ETL, there is no terminology prompt — a BI asset's kind is per-asset display data (`asset_type` on each returned dict), not a connector-level declaration.

Then answer the script's prompt (pipe via stdin if running non-interactively).

This creates `bi_connectors/<name>/` with:
- `connector.py` — `Connector` subclass with a single `fetch_metadata` stub (no `fetch_run_details` — BI assets have no run pipeline)
- `manifest.json` — connector identity with `asset_class: "bi"`
- `credentials.json` — vendor API credential template
- `requirements.txt` — vendor client dependencies

## Step 2: Verify

Confirm the directory was created and list its contents:

**DW:**
```bash
ls -la connectors/<name>/
```

**ETL:**
```bash
ls -la etl_connectors/<name>/
```

**BI:**
```bash
ls -la bi_connectors/<name>/
```

## Step 3: Report and suggest next step

**For DW connectors:**
> Connector `<name>` scaffolded. Next step: run `/setup-connection <name>` to install the database driver and implement the connection methods.

**For ETL connectors:**
> ETL connector `<name>` scaffolded. Next step: run `/implement-etl-connector <name>` to research the vendor API and implement the connector methods.

**For BI connectors:**
> BI connector `<name>` scaffolded. Next step: run `/implement-bi-connector <name>` to research the vendor BI API and implement `fetch_metadata`.
