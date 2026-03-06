---
name: test-and-fix
description: >
  Debugging guide for fixing failing tests in the custom-integration-setup repo.
  Use when any pytest test fails during integration development, when you need to diagnose
  template rendering errors, SQL execution errors, or assertion failures. Reference guide for
  all phases — each phase prompt links here when tests fail.
---

# Test and Fix Guide

Diagnose and fix failing tests for a database integration. Cross-cutting reference for running tests, interpreting failures, and fixing common issues. Each phase prompt references this file — consult it whenever a test fails.

`$ARGUMENTS` is the integration name (auto-detected if only one integration exists in `integrations/`).

**Never read `.env` files or files containing credentials.**

---

## Quick Triage

When tests fail, answer these questions in order:

1. **Is it many tests at once?** → A core dependency is broken. Check `build_cte_template`, `add_select_clause_template`, `add_from_clause_template`, `union_queries_template`, `get_count_all_expression_template`. Fix the core first.
2. **Is it a `UndefinedError` or `TemplateSyntaxError`?** → Jinja variable mismatch. Check the method's docstring for exact variable names.
3. **Is it a SQL syntax error?** → Your dialect differs from the template. Run the rendered SQL directly in your DB client.
4. **Is it an assertion error (wrong value)?** → Logic issue. Trace the expected vs actual value from the test.
5. **Is it a `TypeError: NoneType`?** → Method not implemented yet (still `pass`). Implement it.

---

## Running Tests

### By phase (gate tests)

```bash
INTEGRATION=<name> pytest -m connection          # Phase 1: 3 tests
INTEGRATION=<name> pytest -m metadata            # Phase 2: up to 9 tests
INTEGRATION=<name> pytest -m custom_monitors     # Phase 3: 3 tests
INTEGRATION=<name> pytest -m query_language      # Phase 4: ~80 tests
```

### By file

```bash
INTEGRATION=<name> pytest tests/test_ql_query_building.py
INTEGRATION=<name> pytest tests/test_ql_comparison.py
INTEGRATION=<name> pytest tests/test_ql_aggregation.py
INTEGRATION=<name> pytest tests/test_ql_string_ops.py
INTEGRATION=<name> pytest tests/test_ql_datetime.py
INTEGRATION=<name> pytest tests/test_ql_type_casting.py
INTEGRATION=<name> pytest tests/test_ql_null_nan.py
INTEGRATION=<name> pytest tests/test_ql_math.py
INTEGRATION=<name> pytest tests/test_ql_advanced.py
```

### Single test (with verbose output)

```bash
INTEGRATION=<name> pytest tests/test_ql_comparison.py::test_equality -v
```

### All tests

```bash
INTEGRATION=<name> pytest
```

---

## Interpreting Failures

### Template rendering error

```
jinja2.exceptions.UndefinedError: 'field' is undefined
```

**Cause:** Your Jinja template references a variable that wasn't passed by the test.
**Fix:** Check the method's docstring for the exact variable names the test passes. Use those names in your template. Variable names are case-sensitive.

### Jinja syntax error

```
jinja2.exceptions.TemplateSyntaxError: unexpected '}'
```

**Cause:** Malformed Jinja in your template string.
**Fix:** Check for unbalanced `{{` / `}}` or `{%` / `%}`. Remember these are inside a Python string — escape any literal braces you need with `{{` and `}}` if you want a literal `{`.

### SQL execution error

```
ProgrammingError: syntax error at or near "..."
```

**Cause:** The rendered template produces invalid SQL for your database dialect.
**Fix:** Add a `print(rendered_query)` before the execute call, see what SQL was generated, and run it directly in your database client. Adjust syntax to match your dialect.

### Assertion error

```
AssertionError: assert 0 == 1
```

**Cause:** The query ran but returned the wrong result.
**Fix:** The test expected a specific value. Check your template logic — e.g., `>=` vs `>`, inclusive vs exclusive ranges, missing `COUNT(*)` alias, off-by-one in date arithmetic.

### `TypeError: 'NoneType' object is not iterable` or `AttributeError: 'NoneType'`

**Cause:** A method returns `None` (still has `pass` as its body).
**Fix:** Implement the method. It must return a string.

### Many tests fail at once

**Cause:** A core dependency is broken. The most common culprits:
1. `build_cte_template` — nearly every test uses `make_data_source()` which builds CTEs
2. `add_select_clause_template` / `add_from_clause_template` — used in every query
3. `union_queries_template` — used by `make_data_source()` to build multi-row CTEs
4. `get_count_all_expression_template` — used by comparison, aggregation, and datetime tests
5. `alias_field_template` — used by datetime tests to alias timestamp literals

**Fix:** Implement core query building methods first, then re-run.

---

## Dialect Quick Reference

When you know your dialect differs from the examples, use this table:

| Feature | PostgreSQL | Snowflake | BigQuery | MySQL | SQLite |
|---|---|---|---|---|---|
| String cast | `::TEXT` | `::VARCHAR` | `CAST(x AS STRING)` | `CAST(x AS CHAR)` | `CAST(x AS TEXT)` |
| Timestamp cast | `::TIMESTAMP` | `CAST(x AS TIMESTAMP)` | `CAST(x AS TIMESTAMP)` | `CAST(x AS DATETIME)` | — |
| Regex match | `x ~ pattern` | `REGEXP_LIKE(x, p)` | `REGEXP_CONTAINS(x, p)` | `x REGEXP p` | `x REGEXP p` |
| Conditional count | `COUNT(CASE WHEN c THEN 1 END)` | `COUNT_IF(c)` | `COUNTIF(c)` | `COUNT(IF(c,1,NULL))` | `COUNT(CASE WHEN c THEN 1 END)` |
| Safe divide | `CASE WHEN d=0 THEN NULL ELSE n/d END` | `DIV0(n, d)` | `SAFE_DIVIDE(n, d)` | `IF(d=0, NULL, n/d)` | `CASE WHEN d=0 THEN NULL ELSE n/d END` |
| Date add | `x + INTERVAL '1 day'` | `DATEADD(day, 1, x)` | `DATE_ADD(x, INTERVAL 1 DAY)` | `DATE_ADD(x, INTERVAL 1 DAY)` | `DATE(x, '+1 day')` |
| Epoch seconds | `EXTRACT(EPOCH FROM x)` | `DATE_PART('epoch', x)` | `UNIX_SECONDS(x)` | `UNIX_TIMESTAMP(x)` | `strftime('%s', x)` |
| Row limit | `LIMIT n` | `LIMIT n` | `LIMIT n` | `LIMIT n` | `LIMIT n` |
| Date truncate | `DATE_TRUNC('day', x)` | `DATE_TRUNC('day', x)` | `DATE_TRUNC(x, DAY)` | `DATE(x)` | `DATE(x)` |

---

## Common Patterns

### One-liner templates

Most templates are one-liners. For example:
```python
def get_avg_function_template(self) -> str:
    return "AVG({{ field }})"
```

### Composed templates

Some tests compose multiple templates together. For example, `test_is_yesterday` builds a CTE with timestamp literals, then filters with `get_is_yesterday_expression_template`. If this test fails, check that `literal_datetime_template`, `alias_field_template`, `build_cte_template`, and `union_queries_template` all work correctly first.

### Boolean flags

Four methods return `"true"` or `"false"` as plain strings (not Jinja templates):
- `supports_literal_select_template`
- `supports_literal_group_by_template`
- `supports_group_by_on_subquery_template`
- `parses_timestamp_with_trailing_text_template`

---

## capabilities.json

After each test run, the test suite generates `output/<name>/capabilities.json`. This file contains:

- **`templates`**: Pass/fail/skip status for every `@pytest.mark.template(func="...")` method
- **`capabilities`**: Boolean flags derived from `@pytest.mark.capability(...)` tests (e.g., `supports_volume_rows`, `supports_freshness`)
- **`metrics`**: Which Monte Carlo metrics your integration supports, derived from template pass/fail status via `qlbase_method_metrics_mapping.csv`

Do **not** edit this file manually — it is auto-generated. Use it to track your progress and identify which methods still need implementation.

---

## Debug Workflow

1. Run the failing test with `-v` for verbose output
2. Read the error message — it tells you which template failed and why
3. Check the method's docstring in `integrations/_base/integration.py` for examples
4. If the template renders but SQL fails, try the rendered SQL directly in your database client
5. Fix the template, re-run the single test
6. Once the single test passes, re-run the full phase gate

---

## Running in Docker

If the database runs in a container, ensure the container is running before tests:

```bash
docker-compose up -d   # if using the provided docker-compose.yml
```

For databases running on localhost inside Docker that tests connect to from the host, use `host.docker.internal` (macOS/Windows) or the container's IP as the host in your `.env`. If tests run inside Docker too, use the service name from `docker-compose.yml`.
