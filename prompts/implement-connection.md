# Phase 1: Implement Connection (BaseIntegration)

Implement the 6 methods in `BaseIntegration` that establish and manage the database connection. These must work before any template tests can run.

## Prerequisites

1. A `.env` file exists at `integrations/<name>/.env` with database credentials (provided by a human).
2. Your database driver is listed in `integrations/<name>/requirements.txt` and installed.

## Methods

### 1. `credential_env_vars()` → `dict[str, str]`

Map logical credential keys to the environment variable names in your `.env` file. The keys you choose here become the keys you use in `self.credentials` throughout the other methods.

**PostgreSQL example:**
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

**Snowflake example:**
```python
def credential_env_vars(self) -> dict[str, str]:
    return {
        "account": "SNOWFLAKE_ACCOUNT",
        "user": "SNOWFLAKE_USER",
        "password": "SNOWFLAKE_PASSWORD",
        "warehouse": "SNOWFLAKE_WAREHOUSE",
        "database": "SNOWFLAKE_DATABASE",
    }
```

### 2. `create_connection()` → `Any`

Create and return a database connection using `self.credentials`.

**PostgreSQL example:**
```python
import psycopg2

def create_connection(self):
    return psycopg2.connect(
        host=self.credentials["host"],
        port=int(self.credentials["port"]),
        dbname=self.credentials["database"],
        user=self.credentials["user"],
        password=self.credentials["password"],
    )
```

**Snowflake example:**
```python
import snowflake.connector

def create_connection(self):
    return snowflake.connector.connect(
        account=self.credentials["account"],
        user=self.credentials["user"],
        password=self.credentials["password"],
        warehouse=self.credentials["warehouse"],
        database=self.credentials["database"],
    )
```

### 3. `create_cursor()` → `Any`

Create and return a cursor from the active connection. Called immediately after `create_connection()`.

```python
def create_cursor(self):
    return self.connection.cursor()
```

### 4. `execute_query(query: str)` → `None`

Execute a SQL query string using the active cursor.

```python
def execute_query(self, query: str):
    self.cursor.execute(query)
```

### 5. `fetch_all_results()` → `List[Any]`

Fetch and return all rows from the last executed query as a list of tuples.

```python
def fetch_all_results(self):
    return self.cursor.fetchall()
```

### 6. `close_connection()` → `None`

Clean up the cursor and connection.

```python
def close_connection(self):
    self.cursor.close()
    self.connection.close()
```

## Validation

Run the gate tests:

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
| `ModuleNotFoundError` | Driver not installed | Add driver to `requirements.txt` and run `pip install -r integrations/<name>/requirements.txt` |
| `connection refused` | Wrong host/port or DB not running | Check `.env` values, verify DB is accessible |
| `authentication failed` | Wrong user/password | Check `.env` credentials |
| `credential_env_vars returned empty dict` | Method not implemented | Return the dict mapping logical keys to env var names |

## Next Step

Proceed to [Phase 2: Metadata](implement-metadata.md). If tests fail, consult [test-and-fix.md](test-and-fix.md).
