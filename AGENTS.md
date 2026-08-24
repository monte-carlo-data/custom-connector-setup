# Agent Instructions

The connector workflow is driven by four Claude Code skills. Run them in order:

| Step | Skill                                                         | What it does                                                              |
| ---- | ------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 1    | `/create-connector <name>`                                    | Scaffold a new connector directory                                        |
| 2    | `/setup-connection <name>`                                    | Install driver, implement connection methods, verify with `-m connection` |
| 3    | `/implement-connector <name> [hybrid]`                        | Implement all template methods section by section                         |
| 4    | `/build-agent-image <name> [--mode MODE]` | Export capabilities and build Docker image                                |

Each skill file (`.claude/skills/*/SKILL.md`) contains detailed step-by-step instructions. Use `/implement-connector <name> hybrid` for connectors where metadata is pushed externally.

**Credentials validation:** The scaffolded `manifest.json` includes an optional `credentials_schema` field (cerberus format) that enables server-side validation of self-hosted credentials. See [README section 5b](README.md#5b-add-a-credentials-schema-optional) for format details.

## System Dependencies

If a connector needs system-level packages (ODBC drivers, native libraries), add them to `connectors/<name>/Dockerfile.extra` as raw Dockerfile instructions (`RUN`, `ENV`, `ARG`), then regenerate the test Dockerfile:

```bash
python scripts/generate_test_dockerfile.py
docker compose build
```

The `Dockerfile.extra` contents are automatically included in the agent image built by `generate_agent_image.py`.

## Quick Reference: Test Commands

```bash
# Connection
CONNECTOR=<name> docker compose run --rm test -m connection

# Metadata (full mode)
CONNECTOR=<name> docker compose run --rm test -m metadata

# Custom SQL monitors
CONNECTOR=<name> docker compose run --rm test -m custom_monitors

# Query language prerequisites
CONNECTOR=<name> docker compose run --rm test -m ql_prerequisites

# Query language metrics
CONNECTOR=<name> docker compose run --rm test -m ql_metrics

# Functional validation (optional)
CONNECTOR=<name> docker compose run --rm test -m functional

# All tests
CONNECTOR=<name> docker compose run --rm test

# Single test
CONNECTOR=<name> docker compose run --rm test tests/test_ql_prerequisites.py::test_equality -v

# Export capabilities
CONNECTOR=<name> docker compose run --rm test --export
```

## ETL Connector Workflow

ETL connectors monitor pipeline tools (Coalesce, Talend, etc.) by returning structured dicts with run/metadata events. Each connector is a self-contained `Connector` class (same pattern as DW connectors) and doesn't require SQL templates.

**Reference implementation:** this repo ships no worked ETL example. Study the public [Matillion DPC (Maia) connector](https://github.com/monte-carlo-data/mcd-public-resources/tree/main/custom_connectors/matillion_maia) (in `monte-carlo-data/mcd-public-resources`) for a complete `fetch_metadata`/`fetch_run_details` implementation before writing your own.

**Terminology note:** the manifest maps `job` and `task` (always required) and optionally `group`. `group` only applies when the vendor hosts the same job across multiple named environments (e.g. Dev/Prod); most connectors omit it entirely — do not invent a group where the vendor has none.

The ETL workflow has its own Claude Code skills:

| Step | Skill                                                                                           | What it does                                                  |
| ---- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| 1    | `/create-connector <name> --etl`                                                                | Scaffold ETL connector with prompts for terminology and optional icon URL   |
| 2    | `/implement-etl-connector <name>`                                                               | Research vendor API, implement connector methods, verify with tests |
| 3    | `/validate-etl-connector <name>`                                                                | Print one asset + one recent run as JSON to inspect the mapping before building |
| 4    | `/build-agent-image <name>`                                                                     | Build deployable agent image (auto-detects connector type)    |

Each skill file (`.claude/skills/*/SKILL.md`) contains detailed step-by-step instructions.

### ETL Test Commands

```bash
# Connection
CONNECTOR=<name> docker compose run --rm test -m etl_connection

# Metadata
CONNECTOR=<name> docker compose run --rm test -m etl_metadata

# Run details
CONNECTOR=<name> docker compose run --rm test -m etl_run_details

# All ETL tests
CONNECTOR=<name> docker compose run --rm test -m etl_connection,etl_metadata,etl_run_details

# Inspect output — print one asset + one recent run as JSON (post-implementation gate).
# Not a pytest run, so override the entrypoint.
CONNECTOR=<name> docker compose run --rm --entrypoint python test \
  scripts/validate_etl_connector.py
```

Each test group includes **capability tests** that probe optional features (groups, tasks, lineage, schedule, error details, webhook mode, etc.). Features absent from the returned data show as `xfail`. After the tests, an **ETL Capability Summary** prints showing which features are implemented — review it to identify opportunities to enrich the connector.

## Telemetry Connector Workflow

**Status: proof of concept.** Telemetry connectors serve on-demand runtime log and telemetry retrieval for the Troubleshooting Agent. Unlike DW and ETL connectors, they are not on a collection schedule: Monolith resolves the telemetry connection attached to a Warehouse or ETL integration, checks the capability, and invokes the connector synchronously through the Data Collector. The result is returned to the caller and never stored.

**Reference implementation:** `telemetry_connectors/datadog/` — Datadog Logs Search API for `fetch_logs`, Metrics Query API for `fetch_telemetry`. Study it before writing your own.

There are no Claude Code skills for this workflow yet. Steps:

```bash
# 1. Scaffold — prompts for which capabilities the connector supports
python scripts/create_connector.py <name> --telemetry

# 2. Implement telemetry_connectors/<name>/connector.py, then fill in credentials.json

# 3. Fetch and validate one page — stands in for the call Monolith makes during an
#    investigation. Not a pytest run, so override the entrypoint.
CONNECTOR=<name> RESOURCE_ID=<vendor-resource-id> \
  docker compose run --rm --entrypoint python test \
  scripts/validate_telemetry_connector.py

# 4. Build
python scripts/generate_agent_image.py <name>
```

Optional environment variables for step 3: `WINDOW_HOURS` (default 1), `PAGE_SIZE` (default 10), `SEARCH_REGEX`, `SEVERITY`, `TELEMETRY_NAMES`.

**Contract rules that trip people up:**

- `capabilities.supports_logs` / `capabilities.supports_telemetry` in `manifest.json` are the routing contract. Monte Carlo only calls what is advertised — declare only what you actually implement. At least one is required or the image build fails.
- Every query must be scoped to the `resource_id` argument. Never return records for a resource that wasn't asked for.
- Items are timezone-aware ISO 8601, ordered by `timestamp` ascending. `start_time` is inclusive, `end_time` exclusive.
- `cursor`/`next_cursor` are opaque to Monte Carlo — carry whatever the vendor's pagination needs. `None` means last page.
- An empty page (`{"items": [], "next_cursor": None}`) is a valid, correct result. Never raise for no results.
- Push filters (`search_regex`, `severity`, `names`) into the vendor query where the API supports it, and apply the rest to the page yourself — but always honor them.

See the full contract in `telemetry_connectors/_base/connector.py` and README → "Telemetry Connector Quick Start".

### Combined Agent Images

To ship connectors of different kinds in a single agent image, pass them together — the script resolves each name to its directory and detects the type:

```bash
python scripts/generate_agent_image.py <dw-name> <etl-name> <telemetry-name>
```
