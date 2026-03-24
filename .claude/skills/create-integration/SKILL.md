---
name: create-integration
description: Scaffold a new integration directory with base template, manifest, .env, and requirements.txt
argument-hint: <integration-name>
disable-model-invocation: true
---

# Create Integration: Scaffold a New Integration

## Arguments

`$ARGUMENTS` contains the integration name (required). Example: `snowflake`, `bigquery`, `redshift`.

## Step 1: Run the scaffold script

```bash
python scripts/create_integration.py <integration-name>
```

This creates `integrations/<name>/` with:
- `integration.py` — base template with all stubs
- `manifest.json` — unique connection type identifier
- `.env` — empty credentials file
- `requirements.txt` — empty driver file

## Step 2: Verify

Confirm the directory was created and list its contents:

```bash
ls -la integrations/<name>/
```

## Step 3: Report and suggest next step

Print a summary of what was created and suggest:

> Integration `<name>` scaffolded. Next step: run `/setup-connection <name>` to install the database driver and implement the connection methods.
