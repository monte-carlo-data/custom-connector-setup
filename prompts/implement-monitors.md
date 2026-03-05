# Phase 3: Implement Custom SQL Monitors (CustomSQLMonitorTemplates)

Implement 3 Jinja template methods that enable custom SQL monitor functionality. These are simple wrappers used by the platform to count rows, limit results, and express `COUNT(*)`.

## Prerequisites

Phase 2 (metadata) core tests pass: `INTEGRATION=<name> pytest -m metadata`

## Methods

| # | Method | Jinja Variables | Returns | Notes |
|---|---|---|---|---|
| 1 | `transform_into_count_query_template` | `query` | `SELECT COUNT(*) FROM ({{ query }}) ...` | Must alias the subquery |
| 2 | `add_row_limit_template` | `query`, `limit` | `{{ query }} LIMIT {{ limit }}` | Appends limit clause |
| 3 | `get_count_all_expression_template` | _(none)_ | `COUNT(*)` | Used extensively by other tests |

### Implementation Notes

**`transform_into_count_query_template`** wraps any query in a `COUNT(*)` outer query. Most databases require a subquery alias:
```
SELECT COUNT(*) FROM ({{ query }}) AS count_query
```

**`add_row_limit_template`** appends a limit clause. For most databases:
```
{{ query }} LIMIT {{ limit }}
```

**`get_count_all_expression_template`** is just the `COUNT(*)` expression. Nearly every database uses:
```
COUNT(*)
```

> **Important:** `get_count_all_expression_template` is reused heavily by query language tests (comparison, aggregation, datetime, etc.). If this method is wrong, many Phase 4 tests will also fail.

## Validation

Run the gate tests:

```bash
INTEGRATION=<name> pytest -m custom_monitors
```

**Expected:** 3 tests pass:
- `test_transform_into_count_query` — wraps a 3-row CTE in COUNT(*), expects result `3`
- `test_add_row_limit` — limits a 10-row CTE to 5 rows
- `test_count_all_expression` — COUNT(*) on a 4-row CTE, expects result `4`

Note: these tests use `make_data_source()` which depends on core query building templates (`build_cte_template`, `add_select_clause_template`, `add_from_clause_template`, `union_queries_template`). If custom monitor tests fail with template rendering errors, you may need to implement the core query building methods from Phase 4 first, then come back.

**Do not proceed to Phase 4 until all 3 tests pass.**

## Next Step

Proceed to [Phase 4: Query Language](implement-ql.md). If tests fail, consult [test-and-fix.md](test-and-fix.md).
