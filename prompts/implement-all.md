---
name: implement-all
description: >
  Orchestrator skill for implementing a complete database integration in the custom-integration-setup repo.
  Use this skill whenever a user asks to implement a new integration, set up a database connector, or run
  through all phases of the integration workflow. Coordinates Phases 1–4 with gate checks between each.
---

# Implement All Phases (Orchestrator)

Sequentially implement Phases 1–4 for a database integration with gate checks between each phase.

## Determine the Integration Name

Set `INTEGRATION` for every command below. Two cases:

1. **Only one directory in `integrations/` (besides `_base`):** use that name automatically.
2. **Multiple integrations exist:** the user must specify. Look for a name passed as an argument, or ask.

```bash
ls integrations/   # shows available names (ignore _base)
```

Export it for the session: `export INTEGRATION=<name>`

## Prerequisites

A human must have already:
- Created `integrations/$INTEGRATION/.env` with credentials
- Implemented `credential_env_vars` and `create_connection` in `BaseIntegration`
- Added the database driver to `integrations/$INTEGRATION/requirements.txt` and installed it

**Verify before starting.** Open `integrations/$INTEGRATION/integration.py` and confirm `credential_env_vars` returns a non-empty dict and `create_connection` has a real implementation. If either is still `pass` or returns `{}`, STOP — a human must complete those first.

**Never read `.env` files or files containing credentials.**

---

## Step 1: Complete Phase 1 (Connection)

Implement the remaining 4 connection methods (`create_cursor`, `execute_query`, `fetch_all_results`, `close_connection`). These are safe for agents — they don't touch credentials. See [`prompts/implement-connection.md`](implement-connection.md) for the method signatures and typical patterns.

Run the gate:
```bash
INTEGRATION=$INTEGRATION pytest -m connection
```

**Expected:** 3 tests pass. If the gate fails because `credential_env_vars` or `create_connection` aren't implemented, STOP and tell the user what's missing. Do not attempt to implement those two methods yourself.

---

## Step 2: Phase 2 — Metadata

Follow [`prompts/implement-metadata.md`](implement-metadata.md) for the 5 metadata query template methods.

Gate check:
```bash
INTEGRATION=$INTEGRATION pytest -m metadata
```

**If core metadata tests fail, STOP and fix before continuing.** (Optional capability tests may xfail — that's fine.) Consult [test-and-fix.md](test-and-fix.md) if needed.

---

## Step 3: Phase 3 — Custom Monitors

Follow [`prompts/implement-monitors.md`](implement-monitors.md) for the 3 monitor template methods.

Gate check:
```bash
INTEGRATION=$INTEGRATION pytest -m custom_monitors
```

**If any test fails, STOP and fix before continuing.** Note: these tests depend on core query building methods from Phase 4 (`build_cte_template`, `add_select_clause_template`, `add_from_clause_template`, `union_queries_template`). If monitor tests fail with template rendering errors before you've touched Phase 4, implement those 4 core methods first, then come back.

---

## Step 4: Phase 4 — Query Language

Follow [`prompts/implement-ql.md`](implement-ql.md). This is the bulk of the work — ~94 methods across 13 subsections. Start with Core Query Building (#1) since it's a dependency for almost everything else.

Gate check:
```bash
INTEGRATION=$INTEGRATION pytest -m query_language
```

**If tests fail, consult [test-and-fix.md](test-and-fix.md) to diagnose and fix.**

---

## Step 5: Final Validation

Run the full test suite:
```bash
INTEGRATION=$INTEGRATION pytest
```

Review `output/$INTEGRATION/capabilities.json` for the complete pass/fail report.

---

## Resuming Mid-Implementation

If implementation was interrupted and you need to resume:

1. Run all gates to see current state:
   ```bash
   INTEGRATION=$INTEGRATION pytest -m connection
   INTEGRATION=$INTEGRATION pytest -m metadata
   INTEGRATION=$INTEGRATION pytest -m custom_monitors
   INTEGRATION=$INTEGRATION pytest -m query_language
   ```
2. Resume from the first phase with failures.
3. Check `output/$INTEGRATION/capabilities.json` if it exists — it shows which templates already pass.

---

## Rules

- **Only edit `integrations/$INTEGRATION/integration.py`.** Do not modify tests, `conftest.py`, or the plugin.
- Every template method must return a **Jinja template string**, not raw SQL or Python logic.
- Do not edit `capabilities.json` — it is auto-generated.
- Read each method's docstring in `integrations/_base/integration.py` before implementing.
