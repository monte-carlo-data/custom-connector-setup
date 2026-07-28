---
name: create-connector
description: Scaffold a new connector directory with base template, manifest, credentials.json, and requirements.txt
argument-hint: <connector-name>
disable-model-invocation: true
---

# Create Connector: Scaffold a New Connector

## Arguments

`$ARGUMENTS` contains the connector name (required) and optionally `--etl`.

Parse `$ARGUMENTS`:
- If `--etl` is present, this is an ETL connector
- Everything else is the connector name
- Default is data warehouse (no flag)

Examples: `snowflake`, `bigquery`, `coalesce --etl`, `talend --etl`.

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

## Step 3: Report and suggest next step

**For DW connectors:**
> Connector `<name>` scaffolded. Next step: run `/setup-connection <name>` to install the database driver and implement the connection methods.

**For ETL connectors:**
> ETL connector `<name>` scaffolded. Next step: run `/implement-etl-connector <name>` to research the vendor API and implement the connector methods.
