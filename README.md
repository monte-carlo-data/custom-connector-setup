# custom-connector-setup

A toolkit for building custom database connectors and ETL pipeline connectors for Monte Carlo. For database (DW) connectors, you implement base classes — providing connection logic and Jinja SQL templates for your database dialect — then run the included test suite to verify correctness and discover which metrics and capabilities your connector supports. For ETL connectors, you implement two Python methods that return structured run events and job metadata from your pipeline orchestrator. Both produce a generic agent image that you host, deploy, and then register in Monte Carlo.

Supports multiple connectors side by side so you can build and test several at once.

## Using an AI Coding Agent

An AI coding agent can handle the entire workflow — from scaffolding and driver installation to implementing all ~100 template methods, running tests, and building the deployable image. You just provide the database credentials.

### Recommended: Claude Code skills

The repo includes skills that automate the full workflow end-to-end for both DW and ETL connectors.

**DW connector workflow:**

| Step | Skill                                                       | What it does                                                                                          |
| ---- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 1    | `/create-connector <name>`                                  | Scaffold a new connector directory                                                                    |
| 2    | `/setup-connection <name>`                                  | Install driver, implement connection methods, stub `credentials.json` — **pauses for you to fill in credentials** |
| 3    | `/implement-connector <name> [hybrid]`                      | Implement all template methods section by section                                                     |
| 4    | `/build-agent-image <name> [--mode MODE]` | Export capabilities and build deployable Docker image                                                 |

**ETL connector workflow:**

| Step | Skill                                                       | What it does                                                                                          |
| ---- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 1    | `/create-connector <name> --etl`                            | Scaffold an ETL connector with interactive terminology prompts                                        |
| 2    | `/implement-etl-connector <name>`                           | Research vendor API, implement `fetch_metadata` and `fetch_run_details`, verify with tests — **pauses for you to fill in credentials** |
| 3    | `/build-agent-image <name>`                                 | Build deployable Docker image (auto-detects connector type)                                           |

The only manual step is filling in `credentials.json` when the implementation skill pauses. Everything else — scaffolding, API research, implementation, testing, and image building — is handled by the skills.

### Fallback: Other AI agents

If you're not using Claude Code, complete steps 1–6 of Quick Start below to set up connectivity, then provide `AGENTS.md` as context to your LLM along with the connector name. The agent will implement all remaining template methods, run tests iteratively, and export capabilities. Resume at step 10 to build the deployable image.

## DW Connector Quick Start

### 1. Create a connector

```bash
python scripts/create_connector.py <name>
```

This creates `connectors/<name>/` with:

- `connector.py` — base classes to implement (copy of the canonical template)
- `manifest.json` — unique `connection_type` identifier
- `credentials.json` — database credentials (gitignored)
- `requirements.txt` — database driver dependencies
- `Dockerfile.extra` — system dependency instructions (empty by default)

### 2. Implement the connector classes

Edit `connectors/<name>/connector.py` and fill in the base classes:

| Class                         | Purpose                                                                                                                                               |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `BaseConnector`               | Connection lifecycle — `create_connection`, `create_cursor`, `execute_query`, `fetch_all_results`, `close_connection`                                  |
| `MetadataQueryTemplates`      | Jinja templates for discovering databases, schemas, tables, and columns                                                                               |
| `QueryLogCollectionTemplates` | Jinja template for fetching query logs                                                                                                                |
| `CustomSQLMonitorTemplates`   | Jinja templates for custom SQL monitor operations (count wrapping, row limits)                                                                        |
| `QueryLanguageTemplates`      | ~90 Jinja templates covering type casting, date/time functions, aggregations, comparisons, string operations, and more                                |
| `FunctionalTestOperations`    | _(Optional)_ Jinja templates for functional validation — DDL/DML operations (create/drop table, insert rows, add/drop columns) that let the test suite run metadata collection before and after each mutation to confirm metrics actually update. This validates that your metadata sources reflect real-time changes. See [Functional Validation Tests](#functional-validation-tests) for details. |

Every template method returns a template string. Most use format-string placeholders like `{x}` (substituted later by the backend); some use Jinja `{{ variable }}` syntax. For example:

```python
def get_avg_function_template(self) -> str:
    return "AVG({x})"                                   # placeholder — {x} substituted later

def get_casting_to_numeric_expression_template(self) -> str:
    return "CAST({{ expression }} AS NUMERIC)"           # Jinja variable — rendered at template time
```

Each method's docstring documents which pattern it uses, the expected variables, and example implementations for common databases. See [How Templates Work](#how-templates-work) for details.

### 3. Add your database driver

Add your driver to `connectors/<name>/requirements.txt`:

```
psycopg2-binary==2.9.9
```

Then rebuild the Docker image:

```bash
docker compose build
```

### 4. Add system dependencies (optional)

If your database driver requires system-level libraries (ODBC drivers, native clients, etc.), add the installation commands to `connectors/<name>/Dockerfile.extra`:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    unixodbc-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
```

Then regenerate the test Dockerfile:

```bash
python scripts/generate_test_dockerfile.py
```

The `Dockerfile.extra` contents are injected into both the test image and the deployable agent image. The `create_connector.py` script and the `/setup-connection` skill regenerate the test Dockerfile automatically — you only need to run the command above if you edit `Dockerfile.extra` manually after initial setup.

`Dockerfile.extra` supports `RUN`, `ENV`, and `ARG` instructions. `COPY` is not supported because the agent image builds in a temporary directory.

### 5. Configure credentials

Add your database credentials to `connectors/<name>/credentials.json`:

```json
{
  "connect_args": {
    "host": "localhost",
    "port": 5432,
    "database": "mydb",
    "user": "myuser",
    "password": "mypassword"
  }
}
```

The keys in `connect_args` are whatever your `create_connection()` method expects via `self.credentials`:

```python
def create_connection(self):
    import psycopg2
    return psycopg2.connect(
        host=self.credentials["host"],
        port=int(self.credentials["port"]),
        database=self.credentials["database"],
        user=self.credentials["user"],
        password=self.credentials["password"],
    )
```

This same JSON format is used for [self-hosted credentials](https://docs.getmontecarlo.com/docs/self-hosted-credentials) when deploying — just swap in production values.

### 6. Build the Docker image

```bash
docker compose build
```

Some database drivers include native libraries built for a specific architecture. If you hit errors loading `.so` files, rebuild with the correct platform:

```bash
docker compose build --build-arg TARGETPLATFORM=linux/amd64
```

Rebuild whenever you change `requirements.txt` or `Dockerfile.extra` (remember to regenerate the test Dockerfile first if you changed `Dockerfile.extra`).

### 7. Verify the connection

```bash
CONNECTOR=<name> docker compose run --rm test -m connection
```

This runs two quick checks: connection creation and cursor creation. Fix any credential or networking issues before moving on.

If only one connector exists, you can omit `CONNECTOR=`:

```bash
docker compose run --rm test -m connection
```

### 8. Implement and test section by section

Work through each section of `connector.py` incrementally. Implement the methods for one section, run its corresponding tests, fix any failures, then move on to the next section.

```bash
# Metadata collection
CONNECTOR=<name> docker compose run --rm test -m metadata

# Query language prerequisites (needed for metric monitors)
CONNECTOR=<name> docker compose run --rm test -m ql_prerequisites

# Query language metric templates
CONNECTOR=<name> docker compose run --rm test -m ql_metrics

# Custom SQL monitors
CONNECTOR=<name> docker compose run --rm test -m custom_monitors

# Functional validation (optional)
CONNECTOR=<name> docker compose run --rm test -m functional
```

Rebuild the Docker image (`docker compose build`) after changing `connector.py` or `requirements.txt`.

### 9. Run the full suite and export

Once all sections pass individually, run the full test suite with `--export` to generate the manifest and passing templates:

```bash
CONNECTOR=<name> docker compose run --rm test --export
```

Note: `--export` requires the full test suite (no `-m` filter).

### 10. Review capabilities

After a full test run with `--export`, `output/<name>/manifest.json` is generated with:

- **connection_type** — unique identifier for this connector
- **connection_name** — connector directory name
- **capabilities** — which features your connector supports (metadata collection, query logs, custom SQL monitors, metric monitors, etc.)
- **metrics** — which metrics your connector supports, derived from template results and the metrics mapping

Passing templates are exported to `output/<name>/templates/`.

### 11. Build a deployable agent image

Once your connector passes tests and templates are exported, package everything into a custom agent image:

```bash
python scripts/generate_agent_image.py
```

This takes the public `montecarlodata/agent:latest-generic` image as a base and layers on your connector artifacts. The resulting custom agent image contains:

- **Exported templates** (`output/<name>/templates/`) — the passing Jinja templates
- **Manifest** (`output/<name>/manifest.json`) — capabilities and supported metrics
- **Connector code** (`connector.py`) — your connection and execution logic
- **Driver dependencies** (`requirements.txt`, `Dockerfile.extra`) — database drivers and system libraries

**Credentials are NOT included in the image.** Your `credentials.json` stays local and is never copied into the image. Production credentials are provided at deploy time via [self-hosted credentials](https://docs.getmontecarlo.com/docs/self-hosted-credentials).

The generic agent is an egress-only agent that works across all supported platforms (Docker Compose, Kubernetes, EKS, AKS, GKE). See [Generic Agent Platforms](https://docs.getmontecarlo.com/docs/generic-agent-platforms) for deployment options.

**Options:**

| Argument/Flag       | Default                          | Description                          |
| ------------------- | -------------------------------- | ------------------------------------ |
| `names`              | auto-discover all                | Positional connector names to include (DW and/or ETL) |
| `--version`          | `latest`                         | Agent base image version             |
| `--docker-platform`  | `linux/amd64`                    | Docker platform for the image        |
| `--tag`              | `custom-agent:{version}-generic` | Output image tag                     |
| `--mode`             | `auto`                           | `auto`, `full`, or `hybrid` — DW connectors only |

Include specific connectors:

```bash
python scripts/generate_agent_image.py postgres mysql
```

Include an ETL connector:

```bash
python scripts/generate_agent_image.py coalesce
```

Combined DW + ETL image:

```bash
python scripts/generate_agent_image.py postgres coalesce
```

When invoked without any names, both DW connectors (from `output/`) and ETL connectors (from `etl_connectors/`) are auto-discovered.

**Modes:**

|                       | Full (default)                           | Hybrid                                                                                   |
| --------------------- | ---------------------------------------- | ---------------------------------------------------------------------------------------- |
| Metadata & query logs | Collected by the agent                   | Pushed externally                                                                        |
| Requires              | `supports_metadata == true`              | `supports_custom_sql_monitor == true`                                                    |
| Metric monitors       | Optional (warning if prereqs incomplete) | Optional (warning if prereqs incomplete)                                                 |
| Classes to implement  | All 5                                    | BaseConnector + CustomSQLMonitorTemplates (+ QueryLanguageTemplates for metric monitors) |

Full mode (default) — the agent handles metadata collection and metric monitors:

```bash
python scripts/generate_agent_image.py
```

Hybrid mode — metadata is pushed externally, the agent only needs metric monitor support:

```bash
python scripts/generate_agent_image.py --mode hybrid
```

Verify the image:

```bash
docker run --rm --entrypoint ls custom-agent:latest-generic /opt/custom-connectors/
```

Then push the agent image to your container registry and deploy. Your local `connectors/<name>/credentials.json` is already in the format needed for [self-hosted credentials](https://docs.getmontecarlo.com/docs/self-hosted-credentials) — just swap in production values and configure them at deploy time.

### 12. Clean up

When you're done, remove the Docker image and any stopped containers:

```bash
docker compose down --rmi local
```

Nothing is installed on your machine — everything runs inside the container.

## ETL Connector Quick Start

ETL connectors monitor pipeline orchestration tools (Coalesce, Talend, Control-M, etc.) by returning structured event data. Unlike DW connectors which provide SQL templates, ETL connectors implement two Python methods that return plain dicts. The agent framework handles pushing data to Monte Carlo.

1. **Create:**

   ```bash
   python scripts/create_connector.py <name> --etl
   ```

2. **Implement:** Edit `etl_connectors/<name>/connector.py` — implement `fetch_metadata()` and `fetch_run_details()`.

3. **Add credentials:** Fill in `etl_connectors/<name>/credentials.json` with your vendor API credentials only.

4. **Test:**

   ```bash
   CONNECTOR=<name> docker compose run --rm test -m etl_connection
   ```

5. **Build:**

   ```bash
   python scripts/generate_agent_image.py --etl-connection <name>
   ```

### Connector contract

```python
class Connector:
    def setup_connection(self): ...          # optional — initialize API client using self.credentials
    def close_connection(self): ...          # optional — clean up sessions
    def fetch_metadata(self, limit, offset) -> list[dict]: ...                            # required
    def fetch_run_details(self, run_ids?, lookback?, limit, offset) -> list[dict]: ...    # required
```

The agent sets `self.credentials` (a dict from `credentials.json`'s `connect_args`) as an attribute before calling any methods — no `__init__` needed. `setup_connection` and `close_connection` are lifecycle hooks for managing API clients or sessions. The two required methods do all the work:

- `fetch_metadata(limit, offset)` — returns dicts describing jobs/tasks (pipelines, workflows, DAGs). Each dict must have `job_source_id` and `name`. This is structural metadata only — no run history. `limit` and `offset` support pagination.
- `fetch_run_details(run_ids?, lookback?, limit, offset)` — returns dicts with status, timing, errors, and task-level details. Each dict must have `job_source_id`, `run_source_id`, `status`, and `event_time`. Operates in two modes:
  - **Polling mode** (`lookback` provided, no `run_ids`): fetch all runs updated within the time window. Used by the agent on a schedule to discover recent activity. `limit`/`offset` paginate results.
  - **Webhook mode** (`run_ids` provided): fetch details for specific runs by ID, regardless of time window. Used when a webhook notifies Monte Carlo about a run (e.g. a failure) and we need error details and task-level breakdown.

### Dict schema reference

Connectors return plain dicts. The expected keys are defined by the dataclass models in [`pycarlo.features.ingestion.etl`](https://github.com/monte-carlo-data/python-sdk/blob/main/pycarlo/features/ingestion/etl/models.py) — these serve as the canonical schema reference. The test validators check returned dicts against this schema, but connector code never imports the models directly.

| Schema | Required keys | Purpose |
| --- | --- | --- |
| `EtlAsset` | `job_source_id`, `name` | Job/task metadata (schedule, owner, inputs/outputs) |
| `EtlRunEvent` | `job_source_id`, `run_source_id`, `status`, `event_time` | Run state changes (start/end time, error details, task runs) |

Common nested dict structures (all optional):

| Structure | Keys | Used in |
| --- | --- | --- |
| group | `source_id` (req), `name`, `group_type`, `schedule`, `attributes` | `EtlAsset` — identifies the workspace/project |
| task | `task_source_id` (req), `name` (req), `task_type`, `description`, `inputs`, `outputs` | `EtlAsset` tasks list |
| error | `message`, `code`, `failure_type` | `EtlRunEvent` — required when status is failed/error |
| schedule | `kind`, `cron_expression`, `interval_seconds`, `event_trigger` | `EtlAsset`, `EtlGroup` |
| owner | `primary_email`, `primary_name` | `EtlAsset` |
| asset_ref | `asset_type`, `role`, `fully_qualified_name` | `EtlAsset`/`EtlTask` inputs/outputs |
| tag | `key`, `value` | `EtlAsset` properties |

Omit `None` values and empty lists from returned dicts — the agent expects sparse dicts with only populated fields.

### Manifest format

```json
{
  "connection_type": "custom-etl-connector-{7hex}",
  "connection_name": "coalesce",
  "asset_class": "etl",
  "terminology": { "group": "Workspace", "job": "Mapping", "task": "Step" }
}
```

The `terminology` field maps Monte Carlo's generic concepts (group, job, task) to the terms your orchestrator uses.

### ETL test commands

```bash
# Connection test
CONNECTOR=<name> docker compose run --rm test -m etl_connection

# Metadata test — validates fetch_metadata returns well-formed dicts
CONNECTOR=<name> docker compose run --rm test -m etl_metadata

# Run details test — validates fetch_run_details returns well-formed dicts
CONNECTOR=<name> docker compose run --rm test -m etl_run_details
```

## Requirements

- [Docker](https://docs.docker.com/get-docker/)

## Project Structure

```
custom-connector-setup/
  connectors/
    _base/                                # Provided — do not edit
      connector.py                        # Canonical template with all base classes
      __init__.py                         # Exports the base classes
    <your-database>/                      # Created by you (one directory per connector)
      connector.py                        # Your implementation (fill in stubs)
      credentials.json                    # Database credentials (gitignored)
      manifest.json                       # {"connection_type": "...", "connection_name": "...", "asset_class": "warehouse"}
      requirements.txt                    # Database driver deps
      Dockerfile.extra                    # System dependency instructions (optional)
  etl_connectors/
    _base/                                # Provided — do not edit
      connector.py                        # Connector template (copied into new connectors)
      validators.py                       # Cross-field validation for returned dicts
    <your-etl-tool>/                      # Created by you
      connector.py                        # Your implementation
      credentials.json                    # Vendor API credentials (gitignored)
      manifest.json                       # connection_type, name, terminology
      requirements.txt                    # Vendor client library deps
      Dockerfile.extra                    # System dependencies (optional)
  output/                                 # Auto-generated by --export (gitignored)
    <your-database>/
      manifest.json                       # Test results and supported features
      templates/                          # Passing .j2 templates
  scripts/                                # Provided
    create_connector.py                   # Scaffolding helper (stdlib only)
    generate_agent_image.py               # Builds deployable custom agent Docker image
    generate_test_dockerfile.py           # Regenerates root Dockerfile from Dockerfile.extra files
  tests/                                  # Provided — do not edit
    conftest.py                           # Test fixtures (TestConnector, Templates, QueryTestHelper)
    capabilities_plugin.py                # Pytest plugin — generates manifest.json
    test_connection.py                    # Connection tests
    test_metadata_collection.py           # Metadata discovery tests
    test_custom_monitors.py               # Custom SQL monitor tests
    test_ql_prerequisites.py              # Prerequisite templates for metric monitors
    test_ql_metrics.py                    # Metric-specific templates (AVG, STDDEV, LENGTH, regexp, etc.)
    test_functional_validation.py         # Functional validation tests (real-time metadata accuracy)
  tests/etl/                              # ETL connector tests
    conftest.py                           # ETL-specific fixtures
    test_etl_connection.py                # ETL connection test
    test_etl_metadata.py                  # ETL metadata test
    test_etl_run_details.py               # ETL run details test
  .claude/
    skills/                               # Claude Code automation skills
      create-connector/SKILL.md           # DW + ETL scaffolding
      setup-connection/SKILL.md           # DW driver + connection
      implement-connector/SKILL.md        # DW template implementation
      implement-etl-connector/SKILL.md    # ETL API implementation
      build-agent-image/SKILL.md          # DW + ETL Docker image
  AGENTS.md                               # Instructions for AI coding agents
  pytest.toml                             # Pytest configuration and markers
  requirements.txt                        # Shared Python dependencies
  Dockerfile                              # Test runner image
  docker-compose.yml                      # Docker Compose configuration
```

## How Templates Work

All customer-provided SQL is expressed as Jinja templates running in a sandboxed environment (`jinja2.sandbox.ImmutableSandboxedEnvironment`). No raw Python code is ingested by the backend — connection and execution logic stays in your deployment only.

Templates produce SQL fragments and come in three flavors:

### Placeholder templates (most common)

These receive **no Jinja variables**. They output Python format-string placeholders like `{x}` that the backend substitutes later via `.format(x=field_name)`. Because they pass through Jinja untouched (single braces aren't Jinja syntax), the rendered template is the format string itself.

```python
def get_avg_function_template(self) -> str:
    return "AVG({x})"                     # {x} is a literal — NOT a Jinja variable

def get_is_gt_expression_template(self) -> str:
    return "{x} > {y}"                    # two placeholders
```

### Parameterized templates

These receive **named Jinja variables** (`{{ var }}`) that the backend passes as keyword arguments at render time. Use these when the template needs actual values to produce correct SQL.

```python
def get_casting_to_numeric_expression_template(self) -> str:
    return "CAST({{ expression }} AS NUMERIC)"

def add_from_clause_template(self) -> str:
    return "{{ select_clause }} FROM {{ from_expression }}"
```

Some templates are **hybrid** — they combine `{x}` placeholders with Jinja variables:

```python
def get_in_past_days_expression_template(self) -> str:
    return "{x} >= CURRENT_DATE - INTERVAL '{{ days }} days'"
```

### Static templates

No variables at all — the rendered output is always the same string.

```python
def current_timestamp_func_template(self) -> str:
    return "CURRENT_TIMESTAMP()"
```

Boolean capability flags are also templates that render to `"true"` or `"false"`:

```python
def supports_literal_select_template(self) -> str:
    return "true"  # SELECT 1 works without FROM
```

Each method's docstring documents which pattern it uses and what variables it expects. Read the docstring before implementing.

## How Tests Work

Tests use the `ql` fixture (a `QueryTestHelper` instance) that bridges your connector and templates:

```python
@pytest.mark.template(func="get_avg_function_template")
def test_avg(ql):
    data = [{"val": 10}, {"val": 20}, {"val": 30}]
    # Placeholder templates: render first, then .format() to substitute {x}
    avg_expr = ql.render(ql.templates.get_avg_function_template).format(x="val")
    result = ql.select_from_data_source(data, avg_expr)
    assert float(result) == pytest.approx(20.0)

@pytest.mark.template(func="get_casting_to_numeric_expression_template")
def test_cast_numeric(ql):
    data = [{"val": "42"}]
    # Parameterized templates: pass Jinja variables as keyword arguments
    cast_expr = ql.render(ql.templates.get_casting_to_numeric_expression_template, expression="val")
    result = ql.select_from_data_source(data, cast_expr)
    assert float(result) == pytest.approx(42.0)
```

The helper builds CTEs from Python dicts, renders templates, executes queries against your real database, and validates results.

## Functional Validation Tests

The standard tests verify that your metadata templates return correct data types, but they don't verify that the data is **real-time**. Functional validation tests catch stale sources (e.g. statistics tables that only update when stats are collected) by making actual database changes and verifying your metadata queries detect them.

### How it works

The tests create a test table, run metadata collection, mutate the table (insert rows, add columns), run collection again, and assert the changes are detected.

### Implementing `FunctionalTestOperations`

Add a `FunctionalTestOperations` class to your `connector.py`. All you need is a table identifier and Jinja templates for basic DDL/DML operations:

```python
class FunctionalTestOperations:
    def get_test_table_identifier(self) -> tuple:
        return ("my_database", "my_schema", "pandora_functional_test")

    def create_test_table_template(self) -> str:
        return "CREATE TABLE {{ schema }}.{{ table }} (id SERIAL PRIMARY KEY, value TEXT)"

    def insert_rows_template(self) -> str:
        return "INSERT INTO {{ schema }}.{{ table }} (value) SELECT 'row_' || g FROM generate_series(1, {{ num_rows }}) g"

    def add_column_template(self) -> str:
        return "ALTER TABLE {{ schema }}.{{ table }} ADD COLUMN {{ column_name }} {{ column_type }}"

    def drop_column_template(self) -> str:
        return "ALTER TABLE {{ schema }}.{{ table }} DROP COLUMN {{ column_name }}"

    def drop_test_table_template(self) -> str:
        return "DROP TABLE IF EXISTS {{ schema }}.{{ table }}"

    def create_lineage_query_template(self) -> str:
        return "SELECT * FROM {{ schema }}.{{ table }} WHERE 1=0"
```

`get_test_table_identifier()` returns `(database, schema, table)` — the single source of truth for the test table identity. The framework injects these as `{{ database }}`, `{{ schema }}`, and `{{ table }}` into every template, so the table name in the SQL always matches what the tests look for in metadata results.

### What the tests verify

| Test                                   | What it validates                              |
| -------------------------------------- | ---------------------------------------------- |
| `test_table_discovery_after_create`    | New table appears in metadata                  |
| `test_table_discovery_after_drop`      | Dropped table disappears from metadata         |
| `test_volume_change_after_insert`      | `row_count` increases after insert             |
| `test_byte_count_change_after_insert`  | `byte_count` increases after insert            |
| `test_freshness_change_after_insert`   | `last_update_time` advances after insert       |
| `test_schema_change_after_add_column`  | New column appears in column metadata          |
| `test_schema_change_after_drop_column` | Dropped column disappears from column metadata |
| `test_query_log_capture`               | Executed query appears in query logs           |

Tests auto-skip when stubs are not implemented or when the relevant feature (row_count, freshness, columns, query logs) is not supported by your connector.

### Running functional tests

```bash
CONNECTOR=<name> docker compose run --rm test -m functional
```

## Advanced Usage

### Testing with a local agent build

By default, `generate_agent_image.py` pulls the public `montecarlodata/agent` image from DockerHub as the base. If you need to test against a local or unreleased version of the agent, you can build the [apollo-agent](https://github.com/monte-carlo-data/apollo-agent) image locally and use `--base-image` to point at it:

```bash
# Clone and build the agent locally
git clone https://github.com/monte-carlo-data/apollo-agent.git
cd apollo-agent
docker build -t local-agent .

# Use the local build as the base for your custom image
cd /path/to/custom-connector-setup
python scripts/generate_agent_image.py --base-image local-agent
```

This is useful for debugging agent-side behavior or verifying your connector works with in-development agent changes before they're published.
