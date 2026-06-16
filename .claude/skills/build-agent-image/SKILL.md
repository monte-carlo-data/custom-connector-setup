---
name: build-agent-image
description: Export capabilities and build a custom agent Docker image for one or more connectors
argument-hint: <connector-name> [<connector-name>...] [--mode MODE]
disable-model-invocation: false
---

# Build Agent Image: Export and Build Docker Image

## Arguments

`$ARGUMENTS` contains:
- One or more connector names (required): e.g., `postgres`, `coalesce`, `postgres coalesce`
- `--mode MODE` (optional): `full`, `hybrid`, or `auto`. Default: `auto` (DW only; ignored for ETL)

Parse any flags from `$ARGUMENTS`. Anything not prefixed with `--` is a connector name.

**If no connector name is provided:** List the available connectors under both `connectors/`
and `etl_connectors/` (excluding `_base`) and ask the user which one(s) to build. Do not proceed
until they respond.

## Step 1: Detect connector types and verify files

For each connector name, **auto-detect** whether it is a DW or ETL connector by checking which
directory it exists in:
- `connectors/<name>/` → DW connector
- `etl_connectors/<name>/` → ETL connector

**If found in neither directory:** Stop and tell the user the connector was not found. Suggest
running `/create-connector <name>` (DW) or `/create-connector <name> --etl` (ETL).

**If found in both directories:** Ask the user which one they mean and wait for a response.

**For each DW connector**, check that these files exist:
- `connectors/<name>/connector.py`
- `connectors/<name>/manifest.json`
- `connectors/<name>/requirements.txt`

If any are missing, stop and tell the user to run `/create-connector <name>` first.

Note: If `connectors/<name>/Dockerfile.extra` exists with system dependency instructions, those are automatically included in the agent image build — no extra steps needed.

**For each ETL connector**, check that these files exist:
- `etl_connectors/<name>/connector.py`
- `etl_connectors/<name>/manifest.json`

If any are missing, stop and tell the user to run `/create-connector <name> --etl` first.

ETL connectors do not require an export step — the `manifest.json` in `etl_connectors/<name>/` is the single source of truth (status mappings are authored there directly). Skip Steps 2–4 and go directly to Step 5.

## Step 2: Check for existing export

Check if `output/<name>/manifest.json` already exists:

```bash
ls output/<name>/manifest.json 2>/dev/null
```

**If it exists:** Ask the user whether to re-export or use the existing export. If they want to re-export, continue to Step 3. If they want to use existing, skip to Step 4.

**If it doesn't exist:** Continue to Step 3.

## Step 3: Export capabilities

Run the full test suite with `--export`:

```bash
CONNECTOR=<name> docker compose run --rm test --export
```

This generates `output/<name>/manifest.json` and `output/<name>/templates/`. If tests fail, report the failures and stop — the connector needs fixing before an image can be built.

## Step 4: Choose connectors to include in the image

The agent image can bundle **multiple connectors**. Before building, check if
there are other connectors in the repo that already have exports.

**Scan for other exported connectors:**

```bash
ls -d output/*/manifest.json 2>/dev/null
```

Any directory under `output/` with a `manifest.json` is a connector that has been
previously exported and can be included.

**If other exported connectors exist besides the one from `$ARGUMENTS`:**

Present the user with the full list and ask which ones to include. Format the
prompt like this:

> The following connectors have been exported and can be included in the agent image:
>
> 1. **`oracle_db_11`** ← the connector you just built
> 2. **`cockroachdb`** — previously exported
> 3. **`microsoft_fabric`** — previously exported
>
> Which connectors should be included? Options:
> - **all** — include everything (default)
> - **only `oracle_db_11`** — just the one you're working on
> - Or list specific names, e.g. `oracle_db_11, cockroachdb`

Wait for the user to respond before proceeding.

**If no other exported connectors exist:** Skip this step — the image will contain
only the connector from `$ARGUMENTS`.

## Step 5: Build the Docker image

Build the command from the detected types (Step 1) and the user's selection in Step 4.

All connector names (DW and ETL) are passed as positional arguments. The script auto-detects each connector's type from its directory.

```bash
echo y | python scripts/generate_agent_image.py \
  <name1> <name2> <name3> \
  --mode <mode>
```

Where:
- All connector names are positional arguments (DW and ETL mixed freely)
- `<mode>` is from arguments or defaults to `auto` (applies to DW connectors only)
- Omit names to auto-discover all connectors

## Step 6: Report results

**If the build succeeds**, report:
- The image tag (e.g., `custom-agent:latest-generic`)
- Which connectors are included in the image (DW and/or ETL) and their modes
- Verification commands:
  - DW: `docker run --rm --entrypoint ls <tag> /opt/custom-connectors/`
  - ETL: `docker run --rm --entrypoint ls <tag> /opt/custom-etl-connectors/`
- Push instructions:
  ```
  docker tag <tag> <your-registry>/<tag>
  docker push <your-registry>/<tag>
  ```
- Remind the user that their credential files (`connectors/<name>/credentials.json` or `etl_connectors/<name>/credentials.json`) are already in the format needed for self-hosted credentials — just swap in production values: https://docs.getmontecarlo.com/docs/self-hosted-credentials

**If the build fails**, read the Docker build output and diagnose:
- Missing base image: user may need to `docker pull` the agent base image
- pip install failure: check `requirements.txt` for correct package names
- Missing artifacts: re-run the export step
