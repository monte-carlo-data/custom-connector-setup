# Agent Instructions

## Objective

Implement all template methods and remaining `BaseIntegration` methods in `integrations/<name>/integration.py`. The connection is already working — a human has implemented `credential_env_vars`, `create_connection`, and `create_cursor`, and verified they pass with `-m connection`. Your job is everything else.

## Scope

| Area | What to implement |
|------|-------------------|
| `BaseIntegration` | `execute_query`, `fetch_all_results`, `close_connection` |
| `MetadataQueryTemplates` | Jinja templates for discovering databases, schemas, tables, and columns |
| `QueryLogCollectionTemplates` | Jinja template for fetching query logs |
| `CustomSQLMonitorTemplates` | Jinja templates for custom SQL monitor operations |
| `QueryLanguageTemplates` | ~90 Jinja templates covering type casting, date/time, aggregations, comparisons, string operations, etc. |
| `FunctionalTestOperations` | *(Optional)* Jinja templates for functional validation — table identity, create/drop, insert, add column, lineage query |

## Rules

- **Only edit `integrations/<name>/integration.py`.** Do not modify any files in `tests/`, `conftest.py`, or the plugin. The tests are the spec.
- Every template method must return a **Jinja template string**, not raw SQL and not Python logic. For example: `return "AVG({{ field }})"`.
- **Do not edit `capabilities.json`.** It is auto-generated when you run `--export`.
- Read each method's docstring before implementing it. The docstring documents the Jinja variables the template receives, example implementations for common databases, and which metrics the method enables.

## Workflow

1. **Implement remaining `BaseIntegration` methods** — `execute_query`, `fetch_all_results`, and `close_connection`. These must work before any template test can run.

2. **Implement templates in sections**, running tests after each:
   - `INTEGRATION=<name> docker compose run --rm test -m metadata` — `MetadataQueryTemplates`
   - `INTEGRATION=<name> docker compose run --rm test -m custom_monitors` — `CustomSQLMonitorTemplates`
   - `INTEGRATION=<name> docker compose run --rm test -m ql_prerequisites` — prerequisite templates in `QueryLanguageTemplates`
   - `INTEGRATION=<name> docker compose run --rm test -m ql_metrics` — metric-specific templates in `QueryLanguageTemplates`
   - `INTEGRATION=<name> docker compose run --rm test -m functional` — functional validation via `FunctionalTestOperations`

3. **Read failures carefully.** A template rendering error means your Jinja string has the wrong variables. A SQL error means the rendered query is invalid for your database. An assertion error means the query ran but returned the wrong result.

4. **Export capabilities.** Run the full suite with `--export` to generate `output/<name>/capabilities.json`:
   ```bash
   INTEGRATION=<name> docker compose run --rm test --export
   ```

### Useful test commands

```bash
# Run all tests
INTEGRATION=<name> docker compose run --rm test

# Run a single test file
INTEGRATION=<name> docker compose run --rm test tests/test_ql_prerequisites.py

# Run a single test
INTEGRATION=<name> docker compose run --rm test tests/test_ql_prerequisites.py::test_equality -v
```

## Hybrid Mode

Hybrid mode is for integrations where metadata is pushed externally. Skip `MetadataQueryTemplates` and `QueryLogCollectionTemplates`. Focus on `CustomSQLMonitorTemplates`, and optionally `QueryLanguageTemplates` to enable metric monitors.

### Hybrid Workflow

1. **Implement remaining `BaseIntegration` methods** — `execute_query`, `fetch_all_results`, `close_connection`.

2. **Implement `CustomSQLMonitorTemplates`** and run:
   ```bash
   INTEGRATION=<name> docker compose run --rm test -m custom_monitors
   ```

3. **(Optional) Implement `QueryLanguageTemplates`** to enable metric monitors. Run `-m ql_prerequisites` then `-m ql_metrics` the same as full mode.

4. **Export capabilities:**
   ```bash
   INTEGRATION=<name> docker compose run --rm test --export
   ```

## Functional Validation (Optional)

After implementing `MetadataQueryTemplates`, you can add `FunctionalTestOperations` to verify that your metadata queries reflect **real-time** database changes — not stale statistics tables.

### What to implement

`FunctionalTestOperations` has one config method and five Jinja templates:

| Method | Returns |
|--------|---------|
| `get_test_table_identifier()` | `(database, schema, table)` tuple — single source of truth for the test table |
| `create_test_table_template()` | Jinja template to CREATE the test table |
| `insert_rows_template()` | Jinja template to INSERT rows (receives `{{ num_rows }}`) |
| `add_column_template()` | Jinja template to ALTER TABLE ADD COLUMN (receives `{{ column_name }}`, `{{ column_type }}`) |
| `drop_test_table_template()` | Jinja template to DROP TABLE IF EXISTS |
| `create_lineage_query_template()` | Jinja template for a SELECT that should appear in query logs |

Every template automatically receives `{{ database }}`, `{{ schema }}`, and `{{ table }}` from `get_test_table_identifier()`. Use these variables in your templates instead of hardcoding the table name — the framework enforces consistency.

### Example (PostgreSQL)

```python
class FunctionalTestOperations:
    def get_test_table_identifier(self) -> tuple:
        return ("monolith", "public", "pandora_functional_test")

    def create_test_table_template(self) -> str:
        return "CREATE TABLE {{ schema }}.{{ table }} (id SERIAL PRIMARY KEY, value TEXT)"

    def insert_rows_template(self) -> str:
        return "INSERT INTO {{ schema }}.{{ table }} (value) SELECT 'row_' || g FROM generate_series(1, {{ num_rows }}) g"

    def add_column_template(self) -> str:
        return "ALTER TABLE {{ schema }}.{{ table }} ADD COLUMN {{ column_name }} {{ column_type }}"

    def drop_test_table_template(self) -> str:
        return "DROP TABLE IF EXISTS {{ schema }}.{{ table }}"

    def create_lineage_query_template(self) -> str:
        return "SELECT * FROM {{ schema }}.{{ table }} WHERE 1=0"
```

### Running

```bash
INTEGRATION=<name> docker compose run --rm test -m functional
```

Tests auto-skip when stubs are not implemented or when the relevant feature is not supported. A failure means your metadata template is likely reading from a stale source.
