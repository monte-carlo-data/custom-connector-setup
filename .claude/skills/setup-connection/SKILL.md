---
name: setup-connection
description: Research the database driver, implement connection methods, stub credentials.json, and verify with connection tests
argument-hint: <connector-name>
disable-model-invocation: true
---

# Setup Connection: Install Driver and Implement Connection Methods

## Arguments

`$ARGUMENTS` contains the connector name (required). Example: `snowflake`, `bigquery`, `redshift`.

## Step 1: Read the connector scaffold

Read these files to understand the current state:
1. `connectors/<name>/connector.py` — the stub file
2. `connectors/<name>/requirements.txt` — currently empty
3. `connectors/<name>/credentials.json` — empty template

## Step 2: Research the database driver

Use web search to find the correct Python database driver for this database. Look for:
- The official or most widely-used Python driver
- Prefer **pure-Python** or **`-binary`** variants (e.g., `psycopg2-binary` over `psycopg2`) — these avoid needing C compiler tooling in Docker
- The correct package name and a recent stable version
- The connection API (constructor arguments, cursor creation)

If web search is unavailable, fall back to training data knowledge.

## Step 3: Add the driver to requirements.txt

Write the driver package with a pinned version to `connectors/<name>/requirements.txt`:

```
# Example:
psycopg2-binary==2.9.9
```

## Step 4: Implement connection methods

Edit `connectors/<name>/connector.py` to implement these two methods in `BaseConnector`:

### `create_connection()`
Import the driver at the top of the file and create a connection using `self.credentials[key]` for each credential key defined in `credentials.json`'s `connect_args`. Follow the driver's documented connection API.

### `create_cursor()`
Return a cursor from `self.connection`. Add any session-level settings if needed (e.g., date format, timezone).

**Do not implement** `execute_query`, `fetch_all_results`, `close_connection`, or any template methods — those come later in `/implement-connector`.

## Step 5: Stub credentials.json

Write `connectors/<name>/credentials.json` with the credential keys your `create_connection()` method expects, using placeholder values:

```json
{
  "connect_args": {
    "host": "",
    "port": 5432,
    "database": "",
    "user": "",
    "password": ""
  }
}
```

This is the same format used for [self-hosted credentials](https://docs.getmontecarlo.com/docs/self-hosted-credentials) in production — the user fills it in once and reuses it for deployment.

## Step 6: STOP — Wait for user to fill in credentials

**You must stop here and tell the user:**

> Connection code is ready. Please fill in your database credentials in `connectors/<name>/credentials.json` and confirm when done so I can run the connection test.

**Do not proceed until the user confirms.** The connection test will fail without real credentials.

## Step 7: Build and run connection test

After user confirms credentials are set:

```bash
docker compose build
CONNECTOR=<name> docker compose run --rm test -m connection
```

## Step 8: Handle results

**If tests pass:** Report success and suggest:
> Connection verified! Next step: run `/implement-connector <name>` to implement all template methods.

**If tests fail:** Read the error output carefully.
- **ImportError**: Driver not installed correctly — check `requirements.txt` spelling and rebuild
- **Connection refused / timeout**: Credentials or network issue — ask user to verify `credentials.json` values
- **Authentication failed**: Wrong username/password — ask user to check credentials
- **SSL/TLS error**: May need SSL parameters in `create_connection()`

Fix what you can in the code, then re-run. For credential issues, ask the user to update `credentials.json` and confirm.
