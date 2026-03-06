---
name: implement-monitors
description: >
  Guide for implementing Phase 3 custom SQL monitor templates in the custom-integration-setup repo.
  Use when implementing transform_into_count_query_template, add_row_limit_template, or
  get_count_all_expression_template. Requires Phases 1 and 2 to already pass.
---

# Phase 3: Implement Custom SQL Monitors (CustomSQLMonitorTemplates)

Implement 3 Jinja template methods that enable custom SQL monitor functionality. These are wrappers used by the platform to count rows, limit results, and express `COUNT(*)`.

## Prerequisites

> **Phase 4 dependency warning:** The tests for this phase use `make_data_source()`, which calls `build_cte_template`, `add_select_clause_template`, `add_from_clause_template`, and `union_queries_template` from Phase 4. If you haven't started Phase 4 yet and these monitor tests fail with template rendering errors (not SQL errors), implement those 4 core Phase 4 methods first, then return here.

- Phase 1 (connection) gate passes.
- Phase 2 (metadata) core tests pass:
  ```bash
  INTEGRATION=$ARGUMENTS pytest -m metadata
  ```
- **Never read `.env` files or files containing credentials.**

`$ARGUMENTS` is the integration name (auto-detected if only one integration exists in `integrations/`).

## Methods

| # | Method | Jinja Variables | Returns | Notes |
|---|---|---|---|---|
| 1 | `transform_into_count_query_template` | `query` | `SELECT COUNT(*) FROM ({{ query }}) AS count_query` | Must alias the subquery |
| 2 | `add_row_limit_template` | `query`, `limit` | `{{ query }} LIMIT {{ limit }}` | Appends limit clause |
| 3 | `get_count_all_expression_template` | _(none)_ | `COUNT(*)` | Used extensively in Phase 4 tests too |

### Implementation Notes

**`transform_into_count_query_template`** wraps any query in a `COUNT(*)` outer query. Most databases require a subquery alias:
```python
return "SELECT COUNT(*) FROM ({{ query }}) AS count_query"
```

Some databases (Oracle, older DB2) require a specific syntax — check your dialect. If `AS` isn't supported before the alias, try without it: `FROM ({{ query }}) count_query`.

**`add_row_limit_template`** appends a limit clause:
```python
return "{{ query }} LIMIT {{ limit }}"
```

For databases that don't support `LIMIT` (SQL Server, Sybase), use `TOP`:
```python
return "SELECT TOP {{ limit }} * FROM ({{ query }}) AS t"
```
Or Oracle's `ROWNUM`:
```python
return "SELECT * FROM ({{ query }}) WHERE ROWNUM <= {{ limit }}"
```

**`get_count_all_expression_template`** is just the `COUNT(*)` expression:
```python
return "COUNT(*)"
```

> `get_count_all_expression_template` is reused heavily across Phase 4 query language tests (comparison, aggregation, datetime, etc.). If this method is wrong, many Phase 4 tests will also fail. Get this one right first.

## Validation

```bash
INTEGRATION=<name> pytest -m custom_monitors
```

**Expected:** 3 tests pass:
- `test_transform_into_count_query` — wraps a 3-row CTE in COUNT(*), expects result `3`
- `test_add_row_limit` — limits a 10-row CTE to 5 rows
- `test_count_all_expression` — COUNT(*) on a 4-row CTE, expects result `4`

**Do not proceed to Phase 4 until all 3 tests pass.**

## Next Step

Proceed to [Phase 4: Query Language](implement-ql.md). If tests fail, consult [test-and-fix.md](test-and-fix.md).

## Rules

- **Only edit `integrations/$ARGUMENTS/integration.py`.** Do not modify tests, `conftest.py`, or the plugin.
- Every template method must return a **Jinja template string**, not raw SQL or Python logic.
- Do not edit `capabilities.json` — it is auto-generated.
- Read each method's docstring in `integrations/_base/integration.py` before implementing.
