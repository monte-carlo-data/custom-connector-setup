# custom-integration-setup

A validation toolkit for building custom database integrations. You implement a set of base classes — providing connection logic and Jinja SQL templates for your database dialect — then run the included test suite to verify correctness and discover which metrics and capabilities your integration supports.

Supports multiple integrations side by side (e.g., postgres + snowflake + teradata) so you can build and test several at once.

## Quick Start

### 1. Create an integration

```bash
python scripts/create_integration.py postgres
```

This creates `integrations/postgres/` with:
- `integration.py` — base classes to implement (copy of the canonical template)
- `manifest.json` — unique `connection_type` identifier
- `.env` — credentials file (gitignored)
- `requirements.txt` — database driver dependencies

### 2. Implement the integration classes

Edit `integrations/postgres/integration.py` and fill in the five base classes:

| Class | Purpose |
|-------|---------|
| `BaseIntegration` | Connection lifecycle — `create_connection`, `create_cursor`, `execute_query`, `fetch_all_results`, `close_connection` |
| `MetadataQueryTemplates` | Jinja templates for discovering databases, schemas, tables, and columns |
| `QueryLogCollectionTemplates` | Jinja template for fetching query logs |
| `CustomSQLMonitorTemplates` | Jinja templates for custom SQL monitor operations (count wrapping, row limits) |
| `QueryLanguageTemplates` | ~90 Jinja templates covering type casting, date/time functions, aggregations, comparisons, string operations, and more |

Every template method returns a Jinja template string. For example:

```python
def get_avg_function_template(self) -> str:
    return "AVG({{ field }})"
```

Each method has a docstring documenting its Jinja variables, example implementations for common databases, and which metrics it enables.

### 3. Add your database driver

Add your driver to `integrations/postgres/requirements.txt`:

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

Add your credentials to `integrations/postgres/.env`:

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
INTEGRATION=postgres docker compose run test -m connection
```

This runs three quick checks: connection creation, cursor creation, and a `SELECT 1` round-trip. Fix any credential or networking issues before moving on.

If only one integration exists, you can omit `INTEGRATION=`:

```bash
docker compose run test -m connection
```

### 7. Run the tests

```bash
# Run all tests
INTEGRATION=postgres docker compose run test

# Run by section
INTEGRATION=postgres docker compose run test -m metadata
INTEGRATION=postgres docker compose run test -m query_language
INTEGRATION=postgres docker compose run test -m custom_monitors

# Export passing templates to .j2 files
INTEGRATION=postgres docker compose run test --export-templates
```

### 8. Review capabilities

After a test run, `output/postgres/capabilities.json` is generated with:

- **connection_type** — unique identifier for this integration (from `manifest.json`)
- **templates** — pass/fail status for each template method
- **capabilities** — boolean flags for optional features (volume rows, freshness, schema, query logs, etc.)
- **metrics** — which metrics your integration supports, derived from template results and the metrics mapping

Passing templates are exported to `output/postgres/templates/` when using `--export-templates`.

### 9. Clean up

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
    _base/
      integration.py              # Read-only canonical template (do not edit)
      __init__.py                 # Exports the 5 base classes
    teradata/                     # One directory per integration
      integration.py              # Your implementation (fill in stubs)
      .env                        # Database credentials (gitignored)
      manifest.json               # {"connection_type": "custom-integration-xxx", "name": "teradata"}
      requirements.txt            # Database driver deps
  output/                         # Generated per-integration output (gitignored)
    teradata/
      capabilities.json           # Auto-generated test results
      templates/                  # Exported .j2 files
  scripts/
    create_integration.py         # Scaffolding helper (stdlib only)
  tests/
    conftest.py                   # Test fixtures (TestIntegration, Templates, QueryTestHelper)
    capabilities_plugin.py        # Pytest plugin — generates capabilities.json
    test_connection.py            # Connection tests
    test_metadata_collection.py   # Metadata discovery tests
    test_custom_monitors.py       # Custom SQL monitor tests
    test_ql_query_building.py     # Core query building (CTE, SELECT, ORDER, CASE, etc.)
    test_ql_type_casting.py       # Core type casting (numeric, string, decimal, timestamp)
    test_ql_comparison.py         # Comparison operators and range checks
    test_ql_datetime.py           # Date/time functions and filters
    test_ql_aggregation.py        # Aggregate functions (AVG, STDDEV, COUNT DISTINCT, etc.)
    test_ql_string_ops.py         # String operations (LENGTH, SUBSTR, regex)
    test_ql_null_nan.py           # NULL and NaN handling
    test_ql_math.py               # Math functions (ABS, RAND)
    test_ql_advanced.py           # Advanced features (UNPIVOT, arrays, epoch seconds)
  pytest.toml                     # Pytest configuration and markers
  requirements.txt                # Shared Python dependencies
  Dockerfile                      # Test runner image
  docker-compose.yml              # Docker Compose configuration
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
