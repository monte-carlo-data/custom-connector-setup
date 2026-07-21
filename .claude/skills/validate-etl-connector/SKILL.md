---
name: validate-etl-connector
description: Fetch one asset and one recent run from an implemented ETL connector and print them as JSON for inspection before building the agent image
argument-hint: <connector-name>
disable-model-invocation: false
---

# Validate ETL Connector: Inspect One Asset + One Run

Runs between `/implement-etl-connector` and `/build-agent-image`. The unit tests confirm the
connector returns *well-formed* dicts; this lets a human (or AI) eyeball how one real job is
actually mapped into Monte Carlo's model before shipping.

## Arguments

`$ARGUMENTS` is the ETL connector name (required). If omitted, list the connectors under
`etl_connectors/` (excluding `_base`) and ask which one.

## Steps

1. Confirm `etl_connectors/<name>/connector.py` is implemented and its ETL tests pass.
2. Run the script inside the Docker test image (it needs the connector's vendor deps; the image
   entrypoint is `pytest`, so override it):

   ```bash
   CONNECTOR=<name> docker compose run --rm --entrypoint python test \
     scripts/validate_etl_connector.py
   ```

   It fetches one asset (`fetch_metadata`, limit 1) and one run (`fetch_run_details`, last 1h,
   limit 1) and prints both as JSON.
3. Read the JSON with the user against the connector's `manifest.json` `terminology`: does the job
   name look right (not an internal id)? Are the tasks the right sub-units? Is the group sensible?
   Are the optional extras (owner, trigger, run_url, schedule) populated where the vendor exposes
   them?
4. If it looks wrong, go back to `/implement-etl-connector`. If it looks right, suggest
   `/build-agent-image <name>`.
