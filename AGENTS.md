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

The ETL workflow has its own Claude Code skills:

| Step | Skill                                                                                           | What it does                                                  |
| ---- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| 1    | `/create-connector <name> --etl`                                                                | Scaffold ETL connector with prompts for terminology and optional icon URL   |
| 2    | `/implement-etl-connector <name>`                                                               | Research vendor API, implement connector methods, verify with tests |
| 3    | `/build-agent-image <name>`                                                                     | Build deployable agent image (auto-detects connector type)    |

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
```

Each test group includes **capability tests** that probe optional features (groups, tasks, lineage, schedule, error details, webhook mode, etc.). Features absent from the returned data show as `xfail`. After the tests, an **ETL Capability Summary** prints showing which features are implemented — review it to identify opportunities to enrich the connector.

### Combined Agent Images

To ship a DW connector and an ETL connector in a single agent image:

```bash
python scripts/generate_agent_image.py <dw-name> <etl-name>
```
