---
name: build-agent-image
description: Export capabilities and build a custom agent Docker image for a connector
argument-hint: <connector-name> [--mode MODE]
disable-model-invocation: true
---

# Build Agent Image: Export and Build Docker Image

## Arguments

`$ARGUMENTS` contains:
- `connector_name` (required): e.g., `postgres`, `snowflake`
- `--mode MODE` (optional): `full` or `hybrid`. Default: `full`

Parse any flags from `$ARGUMENTS`. Anything not prefixed with `--` is the connector name.

## Step 1: Verify connector files exist

Check that these files exist:
- `connectors/<name>/connector.py`
- `connectors/<name>/manifest.json`
- `connectors/<name>/requirements.txt`

If any are missing, stop and tell the user to run `/create-connector <name>` first.

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

## Step 4: Build the Docker image

Run the image generator. Use `echo y |` to auto-accept the metric warning prompt (if it appears):

```bash
echo y | python scripts/generate_agent_image.py \
  --connector <name> \
  --mode <mode>
```

Where:
- `<mode>` is from arguments or defaults to `full`

## Step 5: Report results

**If the build succeeds**, report:
- The image tag (e.g., `custom-agent:latest-generic`)
- Verification command: `docker run --rm --entrypoint ls <tag> /opt/custom-connectors/`
- Push instructions:
  ```
  docker tag <tag> <your-registry>/<tag>
  docker push <your-registry>/<tag>
  ```
- Remind the user that their `connectors/<name>/credentials.json` is already in the format needed for self-hosted credentials — just swap in production values: https://docs.getmontecarlo.com/docs/self-hosted-credentials

**If the build fails**, read the Docker build output and diagnose:
- Missing base image: user may need to `docker pull` the agent base image
- pip install failure: check `requirements.txt` for correct package names
- Missing artifacts: re-run the export step
