---
name: implement-metadata
description: >
  Guide for implementing Phase 2 metadata query templates in the custom-integration-setup repo.
  Use when implementing get_databases_query_template, get_schemas_query_template, get_tables_query_template,
  get_columns_query_template, or get_query_logs_query_template. Requires Phase 1 to already pass.
---

# Phase 2: Implement Metadata (MetadataQueryTemplates + QueryLogCollectionTemplates)

Implement 5 Jinja template methods that let the platform discover databases, schemas, tables, columns, and query logs. Each method returns a Jinja template string — not raw SQL.

## Prerequisites

- Phase 1 (connection) gate passes:
  ```bash
  INTEGRATION=$ARGUMENTS pytest -m connection
  ```
- **Never read `.env` files or files containing credentials.**

`$ARGUMENTS` is the integration name (auto-detected if only one integration exists in `integrations/`).

## Methods

| # | Method | Class | Jinja Variables | Returns |
|---|---|---|---|---|
| 1 | `get_databases_query_template` | MetadataQueryTemplates | _(none)_ | One column: database name |
| 2 | `get_schemas_query_template` | MetadataQueryTemplates | `database_name` | One column: schema name |
| 3 | `get_tables_query_template` | MetadataQueryTemplates | `database_name`, `schemas`, `offset`, `limit` | See column order below |
| 4 | `get_columns_query_template` | MetadataQueryTemplates | `database_name`, `tables` | See column order below |
| 5 | `get_query_logs_query_template` | QueryLogCollectionTemplates | `start_time`, `end_time` (datetime) | Query log rows |

## Column Order Requirements

Tests unpack result rows positionally. The column order in your SELECT must match exactly.

### `get_tables_query_template` — 8 columns

```
database_name, schema_name, table_name, table_type, row_count, byte_count, last_update_time, view_query
```

- `table_type` must be `'table'` or `'view'` (lowercase string literal, not the DB's native type name).
- `row_count`, `byte_count`, `last_update_time`, `view_query` are optional — return `NULL` if not available.
- `schemas` arrives as a comma-separated, single-quoted string (e.g. `'public', 'sales'`). Use it directly in an `IN ({{ schemas }})` clause — do not add extra quoting.
- `last_update_time` must be a datetime value, not a string. If your DB returns it as a string, CAST it to a timestamp type.
- Include `LIMIT {{ limit }} OFFSET {{ offset }}` for pagination.

### `get_columns_query_template` — 3 columns

```
full_table_id, column_name, column_type
```

- `full_table_id` must be `database.schema.table` format — concatenate the three parts with `.` separators. Match the case of identifiers as your DB stores them (usually lowercase for PostgreSQL, uppercase for Snowflake).
- `tables` arrives as a comma-separated, single-quoted list of full table IDs.

## Optional Capability Columns

The test suite automatically detects optional capabilities from the `get_tables_query_template` results:

| Column | Capability | What tests check |
|---|---|---|
| `row_count` (non-NULL for any table) | `supports_volume_rows` | At least one table row has an integer `row_count` |
| `byte_count` (non-NULL for any table) | `supports_volume_bytes` | At least one table row has an integer `byte_count` |
| `last_update_time` (non-NULL for any table) | `supports_freshness` | At least one table row has a datetime `last_update_time` |

If your database doesn't expose these, return `NULL` — the tests will `xfail` gracefully.

## Query Logs (Optional)

`get_query_logs_query_template` is optional. If your database doesn't support query log collection, return `None` (or leave as `pass`). The test will `xfail`.

If implemented, the template receives `start_time` and `end_time` as Python `datetime` objects. Use Jinja filters to format them:

```python
# PostgreSQL example — format as ISO string
return "SELECT query_text, start_time FROM pg_stat_activity WHERE start_time BETWEEN '{{ start_time }}' AND '{{ end_time }}'"
```

Most analytics databases (Snowflake, BigQuery, Redshift) have dedicated query history views. Smaller databases (PostgreSQL, MySQL, SQLite) often don't.

## Validation

```bash
INTEGRATION=<name> pytest -m metadata
```

**Expected:** Up to 9 tests. Core tests that must pass:
- `test_fetch_databases` — at least one database returned
- `test_fetch_schemas` — at least one schema returned
- `test_fetch_tables_and_views` — at least one table/view returned with correct column types
- `test_fetch_columns` — columns returned with `(full_table_id, column_name, column_type)` all as strings

Capability tests that may xfail (acceptable):
- `test_volume_rows`, `test_volume_bytes`, `test_freshness` — xfail if optional columns are all NULL
- `test_get_query_logs` — xfail if not implemented

**Do not proceed to Phase 3 until the core metadata tests pass.**

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| `test_fetch_tables_and_views` fails with wrong column count | SELECT column order is wrong | Match exactly: `database_name, schema_name, table_name, table_type, row_count, byte_count, last_update_time, view_query` |
| `test_fetch_columns` fails — `full_table_id` missing | Not concatenating 3-part identifier | Build: `db \|\| '.' \|\| schema \|\| '.' \|\| table` |
| `test_freshness` fails — type assertion | `last_update_time` returned as string | CAST to TIMESTAMP in your SELECT |
| `table_type` assertion fails | Returning DB native type ('BASE TABLE', 'VIEW ', etc.) | Normalize: `CASE WHEN ... THEN 'table' ELSE 'view' END` |
| `IN ({{ schemas }})` syntax error | Added extra quotes around `{{ schemas }}` | Use `IN ({{ schemas }})` not `IN ('{{ schemas }}')` |

## Next Step

Proceed to [Phase 3: Custom Monitors](implement-monitors.md). If tests fail, consult [test-and-fix.md](test-and-fix.md).

## Rules

- **Only edit `integrations/$ARGUMENTS/integration.py`.** Do not modify tests, `conftest.py`, or the plugin.
- Every template method must return a **Jinja template string**, not raw SQL or Python logic.
- Do not edit `capabilities.json` — it is auto-generated.
- Read each method's docstring in `integrations/_base/integration.py` before implementing.
