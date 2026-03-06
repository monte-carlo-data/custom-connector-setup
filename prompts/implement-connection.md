---
name: implement-connection
description: >
  Guide for implementing Phase 1 database connection methods in the custom-integration-setup repo.
  Use when a user needs to set up database connectivity, implement create_cursor/execute_query/fetch_all_results/close_connection,
  or validate that the connection gate passes. Do NOT use to implement credential_env_vars or create_connection — those are human-only.
---

> **CREDENTIAL SECURITY — READ THIS FIRST**
>
> Agents implement only 4 of the 6 connection methods. The two credential-sensitive methods are **human-only**:
>
> | Method | Who implements | Why |
> |---|---|---|
> | `credential_env_vars` | Human | References `.env` variable names |
> | `create_connection` | Human | Uses credentials to connect |
> | `create_cursor` | Agent | Works on an already-open connection |
> | `execute_query` | Agent | Uses the cursor |
> | `fetch_all_results` | Agent | Uses the cursor |
> | `close_connection` | Agent | Teardown only |
>
> **Never read `.env` files or files containing credentials.**

# Phase 1: Implement Connection (BaseIntegration)

Implement the 4 agent-safe methods in `BaseIntegration`. These build on the connection a human has already opened — no credential access needed.

## Prerequisites

1. A `.env` file exists at `integrations/<name>/.env` (provided by a human — do not read it).
2. The database driver is in `integrations/<name>/requirements.txt` and installed.
3. `credential_env_vars` and `create_connection` are already implemented by a human.

**Verify:** open `integrations/<name>/integration.py` and confirm both methods have real implementations (not `pass` or `return {}`). If they don't, stop and tell the user.

---

## Methods to Implement

### `create_cursor()` → `Any`

Return a cursor from `self.connection`. Called immediately after `create_connection()`.

```python
def create_cursor(self):
    return self.connection.cursor()
```

Most drivers use this pattern. BigQuery and some others don't use cursors — if your driver lacks `.cursor()`, return `self.connection` directly and adjust `execute_query` and `fetch_all_results` accordingly.

### `execute_query(query: str)` → `None`

Execute a SQL string using `self.cursor`.

```python
def execute_query(self, query: str):
    self.cursor.execute(query)
```

### `fetch_all_results()` → `List[Any]`

Return all rows from the last executed query as a list of tuples.

```python
def fetch_all_results(self):
    return self.cursor.fetchall()
```

### `close_connection()` → `None`

Clean up cursor and connection on teardown.

```python
def close_connection(self):
    self.cursor.close()
    self.connection.close()
```

If your driver doesn't have a `cursor.close()` (e.g., BigQuery), just close what exists without error.

---

## Finding the Right Driver

If the driver isn't installed yet:

1. Check `integrations/<name>/requirements.txt` — the driver may already be listed.
2. Install it: `pip install -r integrations/<name>/requirements.txt`
3. If the file is empty or missing the driver, add it. Common drivers:
   - PostgreSQL: `psycopg2-binary`
   - MySQL: `mysql-connector-python` or `PyMySQL`
   - Snowflake: `snowflake-connector-python`
   - BigQuery: `google-cloud-bigquery`
   - SQLite: built into Python (no install needed)
   - DuckDB: `duckdb`

---

## Validation

```bash
INTEGRATION=<name> pytest -m connection
```

**Expected:** 3 tests pass — `test_create_connection`, `test_create_cursor`, `test_execute_simple_query`.

The tests verify:
- `connection` is not `None`
- `cursor` is not `None`
- `SELECT 1` returns `[(1,)]`

**Do not proceed to Phase 2 until all 3 tests pass.**

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | Driver not installed | Add to `requirements.txt`, run `pip install -r integrations/<name>/requirements.txt` |
| `connection refused` | Wrong host/port or DB not running | Check `.env` values, verify DB is accessible |
| `authentication failed` | Wrong credentials | Human must fix the `.env` file |
| `cursor.fetchall() returns list of dicts` | Driver uses dict rows | Wrap: `[tuple(row.values()) for row in self.cursor.fetchall()]` |
| `'NoneType' has no attribute 'cursor'` | `create_connection` not implemented | Human must implement `create_connection` first |

## Next Step

Proceed to [Phase 2: Metadata](implement-metadata.md). If tests fail, consult [test-and-fix.md](test-and-fix.md).
