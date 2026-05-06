---
name: build-agent-image
description: Export capabilities and build a custom agent Docker image for one or more connectors
argument-hint: <connector-name> [--mode MODE]
disable-model-invocation: false
---

# Build Agent Image: Export and Build Docker Image

## Arguments

`$ARGUMENTS` contains:
- `connector_name` (required): e.g., `postgres`, `snowflake`
- `--mode MODE` (optional): `full`, `hybrid`, or `auto`. Default: `auto`

Parse any flags from `$ARGUMENTS`. Anything not prefixed with `--` is the connector name.

**If no connector name is provided:** List the available connectors under `connectors/`
(excluding `_base`) and ask the user which one to build. Do not proceed until they respond.

## Step 1: Verify connector files exist

Check that these files exist:
- `connectors/<name>/connector.py`
- `connectors/<name>/manifest.json`
- `connectors/<name>/requirements.txt`

If any are missing, stop and tell the user to run `/create-connector <name>` first.

Note: If `connectors/<name>/Dockerfile.extra` exists with system dependency instructions, those are automatically included in the agent image build — no extra steps needed.

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

Build the `--connector` flags from the user's selection in Step 4.

Run the image generator. Use `echo y |` to auto-accept the metric warning prompt (if it appears):

```bash
echo y | python scripts/generate_agent_image.py \
  --connector <name1> \
  --connector <name2> \
  --mode <mode>
```

Where:
- Each selected connector gets its own `--connector` flag
- `<mode>` is from arguments or defaults to `auto`

## Step 6: Report results

**If the build succeeds**, report:
- The image tag (e.g., `custom-agent:latest-generic`)
- Which connectors are included in the image and their modes
- Verification command: `docker run --rm --entrypoint ls <tag> /opt/custom-connectors/`
- Push instructions:
  ```
  docker tag <tag> <your-registry>/<tag>
  docker push <your-registry>/<tag>
  ```
- Remind the user that their `connectors/<name>/credentials.json` files are already in the format needed for self-hosted credentials — just swap in production values: https://docs.getmontecarlo.com/docs/self-hosted-credentials

**If the build fails**, read the Docker build output and diagnose:
- Missing base image: user may need to `docker pull` the agent base image
- pip install failure: check `requirements.txt` for correct package names
- Missing artifacts: re-run the export step
