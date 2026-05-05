---
name: create-connector
description: Scaffold a new connector directory with base template, manifest, credentials.json, and requirements.txt
argument-hint: <connector-name>
disable-model-invocation: true
---

# Create Connector: Scaffold a New Connector

## Arguments

`$ARGUMENTS` contains the connector name (required). Example: `snowflake`, `bigquery`, `redshift`.

## Step 1: Run the scaffold script

```bash
python scripts/create_connector.py <connector-name>
```

This creates `connectors/<name>/` with:
- `connector.py` — base template with all stubs
- `manifest.json` — unique connector type identifier
- `credentials.json` — empty credentials template
- `requirements.txt` — empty driver file
- `Dockerfile.extra` — system dependency instructions (empty by default)

## Step 2: Verify

Confirm the directory was created and list its contents:

```bash
ls -la connectors/<name>/
```

## Step 3: Report and suggest next step

Print a summary of what was created and suggest:

> Connector `<name>` scaffolded. Next step: run `/setup-connection <name>` to install the database driver and implement the connection methods.
