# custom-integration-setup

A validation toolkit for building custom database integrations. You implement a set of base classes — providing connection logic and Jinja SQL templates for your database dialect — then run the included test suite to verify correctness and discover which metrics and capabilities your integration supports.

Supports multiple integrations side by side so you can build and test several at once.

## Using an AI Coding Agent

An AI coding agent can implement all the template methods after you set up the database connection. This splits the work: you handle credentials and connectivity, the agent handles the ~100 template methods.

### What you do first

Complete steps 1–6 of Quick Start below:

1. Create the integration scaffold
2. Add your database driver to `requirements.txt`
3. Configure credentials in `.env`
4. Implement `credential_env_vars`, `create_connection`, and `create_cursor` in `integration.py`
5. Build the Docker image
6. Verify connection tests pass (`-m connection`)

### Hand off to the agent

Provide `AGENTS.md` as context to your LLM along with the integration name. The agent will:

- Implement the remaining `BaseIntegration` methods (`execute_query`, `fetch_all_results`, `close_connection`)
- Implement all four template classes (or a subset for hybrid mode)
- Run tests iteratively and fix failures
- Export `capabilities.json` when all tests pass

### Resume at step 9

Once the agent finishes, pick back up at step 9 (Build a deployable agent image) to package and deploy your integration.

## Quick Start

### 1. Create an integration

```bash
python scripts/create_integration.py <name>
```

This creates `integrations/<name>/` with:
- `integration.py` — base classes to implement (copy of the canonical template)
- `manifest.json` — unique `connection_type` identifier
- `.env` — credentials file (gitignored)
- `requirements.txt` — database driver dependencies

### 2. Implement the integration classes

Edit `integrations/<name>/integration.py` and fill in the five base classes:

| Class | Purpose |
|-------|---------|
| `BaseIntegration` | Connection lifecycle — `create_connection`, `create_cursor`, `execute_query`, `fetch_all_results`, `close_connection` |
| `MetadataQueryTemplates` | Jinja templates for discovering databases, schemas, tables, and columns |
| `QueryLogCollectionTemplates` | Jinja template for fetching query logs |
| `CustomSQLMonitorTemplates` | Jinja templates for custom SQL monitor operations (count wrapping, row limits) |
| `QueryLanguageTemplates` | ~90 Jinja templates covering type casting, date/time functions, aggregations, comparisons, string operations, and more |
| `FunctionalTestOperations` | *(Optional)* Jinja templates for functional validation — creating/dropping a test table, inserting rows, adding/dropping columns, and a lineage query |

Every template method returns a Jinja template string. For example:

```python
def get_avg_function_template(self) -> str:
    return "AVG({{ field }})"
```

Each method has a docstring documenting its Jinja variables, example implementations for common databases, and which metrics it enables.

### 3. Add your database driver

Add your driver to `integrations/<name>/requirements.txt`:

```
psycopg2-binary==2.9.9
```

Then rebuild the Docker image:

```bash
docker compose build
```

### 4. Configure credentials

Override `credential_env_vars()` in `BaseIntegration` to map credential keys to environment variable names:

```python
def credential_env_vars(self) -> dict[str, str]:
    return {
        "host": "PGHOST",
        "port": "PGPORT",
        "database": "PGDATABASE",
        "user": "PGUSER",
        "password": "PGPASSWORD",
    }
```

Then use `self.credentials` in `create_connection()`:

```python
def create_connection(self):
    import psycopg2
    return psycopg2.connect(
        host=self.credentials["host"],
        port=self.credentials.get("port", "5432"),
        database=self.credentials["database"],
        user=self.credentials["user"],
        password=self.credentials["password"],
    )
```

Add your credentials to `integrations/<name>/.env`:

```
PGHOST=localhost
PGPORT=5432
PGDATABASE=mydb
PGUSER=myuser
PGPASSWORD=mypassword
```

### 5. Build the Docker image

```bash
docker compose build
```

Some database drivers include native libraries built for a specific architecture. If you hit errors loading `.so` files, rebuild with the correct platform:

```bash
docker compose build --build-arg TARGETPLATFORM=linux/amd64
```

Rebuild whenever you change `requirements.txt` (either root or per-integration).

### 6. Verify the connection

```bash
INTEGRATION=<name> docker compose run --rm test -m connection
```

This runs two quick checks: connection creation and cursor creation. Fix any credential or networking issues before moving on.

If only one integration exists, you can omit `INTEGRATION=`:

```bash
docker compose run --rm test -m connection
```

### 7. Run the tests

```bash
# Run all tests
INTEGRATION=<name> docker compose run --rm test

# Run by section
INTEGRATION=<name> docker compose run --rm test -m metadata
INTEGRATION=<name> docker compose run --rm test -m query_language
INTEGRATION=<name> docker compose run --rm test -m ql_prerequisites
INTEGRATION=<name> docker compose run --rm test -m ql_metrics
INTEGRATION=<name> docker compose run --rm test -m custom_monitors
INTEGRATION=<name> docker compose run --rm test -m functional

# Export capabilities.json and passing templates
INTEGRATION=<name> docker compose run --rm test --export
```

Note: `--export` requires the full test suite (no `-m` filter). Use `-m` to iterate on specific test categories, then run the full suite with `--export` when ready.

### 8. Review capabilities

After a full test run with `--export`, `output/<name>/capabilities.json` is generated with:

- **connection_type** — unique identifier for this integration (from `manifest.json`)
- **capabilities** — which features your integration supports (metadata collection, query logs, custom SQL monitors, metric monitors, etc.)
- **metrics** — which metrics your integration supports, derived from template results and the metrics mapping

Passing templates are exported to `output/<name>/templates/`.

### 9. Build a deployable agent image

Once your integration passes tests and templates are exported, package everything into a custom agent image:

```bash
python scripts/generate_agent_image.py --agent-type aws-generic
```

This takes the public `montecarlodata/agent` image as a base and layers on your integration artifacts (templates, capabilities, integration code, and dependencies).

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--agent-type` (required) | — | One of: `aws-generic`, `aws-proxied`, `azure`, `cloudrun`, `lambda` |
| `--version` | `latest` | Agent base image version (e.g. `1.4.12`) |
| `--integration` | all with output/ | Which integrations to include (repeatable) |
| `--docker-platform` | `linux/amd64` | Docker platform for the image |
| `--tag` | `custom-agent:{version}-{agent-type}` | Output image tag |
| `--mode` | `full` | `full` or `hybrid` — see Modes below |

Include specific integrations:

```bash
python scripts/generate_agent_image.py --agent-type aws-generic --integration postgres --integration mysql
```

**Modes:**

| | Full (default) | Hybrid |
|---|---|---|
| Metadata & query logs | Collected by the agent | Pushed externally |
| Requires | `supports_metadata == true` | `supports_custom_sql_monitor == true` |
| Metric monitors | Optional (warning if prereqs incomplete) | Optional (warning if prereqs incomplete) |
| Classes to implement | All 5 | BaseIntegration + CustomSQLMonitorTemplates (+ QueryLanguageTemplates for metric monitors) |

Full mode (default) — the agent handles metadata collection and metric monitors:

```bash
python scripts/generate_agent_image.py --agent-type aws-generic
```

Hybrid mode — metadata is pushed externally, the agent only needs metric monitor support:

```bash
python scripts/generate_agent_image.py --agent-type aws-generic --mode hybrid
```

Verify the image:

```bash
docker run --rm --entrypoint ls custom-agent:latest-aws-generic /opt/custom-integrations/
```

Then push to your container registry and deploy.

### 10. Clean up

When you're done, remove the Docker image and any stopped containers:

```bash
docker compose down --rmi local
```

Nothing is installed on your machine — everything runs inside the container.

## Requirements

- [Docker](https://docs.docker.com/get-docker/)

## Project Structure

```
custom-integration-setup/
  integrations/
    _base/                                # Provided — do not edit
      integration.py                      # Canonical template with all base classes
      __init__.py                         # Exports the base classes
    <your-database>/                      # Created by you (one directory per integration)
      integration.py                      # Your implementation (fill in stubs)
      .env                                # Database credentials (gitignored)
      manifest.json                       # {"connection_type": "custom-integration-xxx", "name": "..."}
      requirements.txt                    # Database driver deps
  output/                                 # Auto-generated by --export (gitignored)
    <your-database>/
      capabilities.json                   # Test results and supported features
      templates/                          # Passing .j2 templates
  scripts/                                # Provided
    create_integration.py                 # Scaffolding helper (stdlib only)
    generate_agent_image.py               # Builds deployable custom agent Docker image
  tests/                                  # Provided — do not edit
    conftest.py                           # Test fixtures (TestIntegration, Templates, QueryTestHelper)
    capabilities_plugin.py                # Pytest plugin — generates capabilities.json
    test_connection.py                    # Connection tests
    test_metadata_collection.py           # Metadata discovery tests
    test_custom_monitors.py               # Custom SQL monitor tests
    test_ql_prerequisites.py              # Prerequisite templates for metric monitors
    test_ql_metrics.py                    # Metric-specific templates (AVG, STDDEV, LENGTH, regexp, etc.)
    test_functional_validation.py         # Functional validation tests (real-time metadata accuracy)
  AGENTS.md                               # Instructions for AI coding agents
  pytest.toml                             # Pytest configuration and markers
  requirements.txt                        # Shared Python dependencies
  Dockerfile                              # Test runner image
  docker-compose.yml                      # Docker Compose configuration
```

## How Templates Work

All customer-provided SQL is expressed as Jinja templates running in a sandboxed environment (`jinja2.sandbox.ImmutableSandboxedEnvironment`). No raw Python code is ingested by the backend — connection and execution logic stays in your deployment only.

Templates receive typed variables and produce SQL fragments:

```python
def get_is_gt_expression_template(self) -> str:
    return "{{ field1 }} > {{ field2 }}"

def get_casting_to_numeric_expression_template(self) -> str:
    return "CAST({{ field }} AS NUMERIC)"

def current_timestamp_func_template(self) -> str:
    return "CURRENT_TIMESTAMP()"
```

Boolean capability flags are also templates that render to `"true"` or `"false"`:

```python
def supports_literal_select_template(self) -> str:
    return "true"  # SELECT 1 works without FROM
```

## How Tests Work

Tests use the `ql` fixture (a `QueryTestHelper` instance) that bridges your integration and templates:

```python
@pytest.mark.template(func="get_avg_function_template")
def test_avg(ql):
    data = [{"val": 10}, {"val": 20}, {"val": 30}]
    avg_expr = ql.render(ql.templates.get_avg_function_template, field="val")
    result = ql.select_from_data_source(data, avg_expr)
    assert float(result) == pytest.approx(20.0)
```

The helper builds CTEs from Python dicts, renders templates, executes queries against your real database, and validates results.

## Functional Validation Tests

The standard tests verify that your metadata templates return correct data types, but they don't verify that the data is **real-time**. Functional validation tests catch stale sources (e.g. statistics tables that only update when stats are collected) by making actual database changes and verifying your metadata queries detect them.

### How it works

The tests create a test table, run metadata collection, mutate the table (insert rows, add columns), run collection again, and assert the changes are detected.

### Implementing `FunctionalTestOperations`

Add a `FunctionalTestOperations` class to your `integration.py`. All you need is a table identifier and Jinja templates for basic DDL/DML operations:

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

| Test | What it validates |
|------|------------------|
| `test_table_discovery_after_create` | New table appears in metadata |
| `test_table_discovery_after_drop` | Dropped table disappears from metadata |
| `test_volume_change_after_insert` | `row_count` increases after insert |
| `test_byte_count_change_after_insert` | `byte_count` increases after insert |
| `test_freshness_change_after_insert` | `last_update_time` advances after insert |
| `test_schema_change_after_add_column` | New column appears in column metadata |
| `test_schema_change_after_drop_column` | Dropped column disappears from column metadata |
| `test_query_log_capture` | Executed query appears in query logs |

Tests auto-skip when stubs are not implemented or when the relevant feature (row_count, freshness, columns, query logs) is not supported by your integration.

### Running functional tests

```bash
INTEGRATION=<name> docker compose run --rm test -m functional
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
cd /path/to/custom-integration-setup
python scripts/generate_agent_image.py --agent-type aws-generic --base-image local-agent
```

This is useful for debugging agent-side behavior or verifying your integration works with in-development agent changes before they're published.
