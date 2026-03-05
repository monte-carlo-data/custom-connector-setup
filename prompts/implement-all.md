# Implement All Phases (Orchestrator)

Sequentially implement Phases 2, 3, and 4 for a database integration with gate checks between each phase.

**Integration:** `$ARGUMENTS` (auto-detected if only one integration exists in `integrations/`)

## Prerequisites

- A human has implemented `credential_env_vars` and `create_connection`. **Never read `.env` files or files containing credentials.**

## Step 1: Complete Phase 1 (Connection)

Verify the human has implemented `credential_env_vars` and `create_connection`. Then implement the remaining 4 connection methods (`create_cursor`, `execute_query`, `fetch_all_results`, `close_connection`) — see [`prompts/implement-connection.md`](implement-connection.md) for examples.

Run the connection gate test:

```bash
INTEGRATION=$ARGUMENTS pytest -m connection
```

**If this fails because `credential_env_vars` or `create_connection` are missing, STOP.** Those must be implemented by a human. Do not read `.env` files.

## Step 2: Phase 2 — Metadata

Follow the instructions in [`prompts/implement-metadata.md`](implement-metadata.md).

Implement: `get_databases_query_template`, `get_schemas_query_template`, `get_tables_query_template`, `get_columns_query_template`, `get_query_logs_query_template`.

Gate check:
```bash
INTEGRATION=$ARGUMENTS pytest -m metadata
```

**If the core metadata tests fail, STOP and fix before continuing.** Consult [test-and-fix.md](test-and-fix.md) if needed.

## Step 3: Phase 3 — Custom Monitors

Follow the instructions in [`prompts/implement-monitors.md`](implement-monitors.md).

Implement: `transform_into_count_query_template`, `add_row_limit_template`, `get_count_all_expression_template`.

Gate check:
```bash
INTEGRATION=$ARGUMENTS pytest -m custom_monitors
```

**If any test fails, STOP and fix before continuing.** Consult [test-and-fix.md](test-and-fix.md) if needed.

## Step 4: Phase 4 — Query Language

Follow the instructions in [`prompts/implement-ql.md`](implement-ql.md).

Implement ~94 methods across 13 subsections, starting with Core Query Building.

Gate check:
```bash
INTEGRATION=$ARGUMENTS pytest -m query_language
```

**If tests fail, consult [test-and-fix.md](test-and-fix.md) to diagnose and fix.**

## Step 5: Final Validation

Run the full test suite:

```bash
INTEGRATION=$ARGUMENTS pytest
```

Review `output/$ARGUMENTS/capabilities.json` for the complete pass/fail report.

## Rules

- **Only edit `integrations/$ARGUMENTS/integration.py`.** Do not modify tests, `conftest.py`, or the plugin.
- Every template method must return a **Jinja template string**, not raw SQL or Python logic.
- Do not edit `capabilities.json` — it is auto-generated.
- Read each method's docstring in `integrations/_base/integration.py` before implementing.
