# Test and Fix Guide

Cross-cutting reference for running tests, interpreting failures, and fixing common issues. Each phase prompt references this file — consult it whenever a test fails.

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

### Single test

```bash
INTEGRATION=<name> pytest tests/test_ql_comparison.py::test_equality -v
```

### All tests

```bash
INTEGRATION=<name> pytest
```

### Running in Docker

If the database runs in a container, ensure the container is running and the `.env` file points to the correct host/port. For databases running on localhost inside Docker, you may need `host.docker.internal` or the container's network IP.

## Interpreting Failures

### Template rendering error

```
jinja2.exceptions.UndefinedError: 'field' is undefined
```

**Cause:** Your Jinja template references a variable that wasn't passed by the test.
**Fix:** Check the method's docstring for the exact variable names the test passes. Use those names in your template.

### SQL execution error

```
ProgrammingError: syntax error at or near "..."
```

**Cause:** The rendered template produces invalid SQL for your database dialect.
**Fix:** Render the template mentally with test data, then try running the SQL directly against your database. Adjust syntax to match your dialect.

### Assertion error

```
AssertionError: assert 0 == 1
```

**Cause:** The query ran but returned the wrong result.
**Fix:** The test expected a specific value. Check that your template logic is correct — e.g., `>=` vs `>`, inclusive vs exclusive ranges, `COUNT(*)` alias requirements.

### `TypeError: 'NoneType' object is not iterable` or `AttributeError: 'NoneType'`

**Cause:** A method returns `None` (still has `pass` as its body).
**Fix:** Implement the method. It must return a string.

### Many tests fail at once

**Cause:** Usually a core dependency is broken. The most common culprits:
1. `build_cte_template` — nearly every test uses `make_data_source()` which builds CTEs
2. `add_select_clause_template` / `add_from_clause_template` — used in every query
3. `union_queries_template` — used by `make_data_source()` to build multi-row CTEs
4. `get_count_all_expression_template` — used by comparison, aggregation, and datetime tests
5. `alias_field_template` — used by datetime tests to alias timestamp literals

**Fix:** Implement core query building methods first, then re-run.

## Common Patterns

### One-liner templates

Most templates are one-liners. For example:
```python
def get_avg_function_template(self) -> str:
    return "AVG({{ field }})"
```

### Dialect-specific syntax

Some templates differ by dialect. Read the docstring examples. Common differences:
- **String cast:** PostgreSQL `TEXT`, Snowflake `VARCHAR`, BigQuery `STRING`
- **Timestamp cast:** PostgreSQL `::TIMESTAMP`, Snowflake `CAST(... AS TIMESTAMP)`, BigQuery `SAFE_CAST(... AS TIMESTAMP)`
- **Regex:** PostgreSQL `~`, Snowflake `REGEXP_LIKE()`, BigQuery `REGEXP_CONTAINS()`
- **Interval arithmetic:** PostgreSQL `+ INTERVAL '1 day'`, Snowflake `DATEADD(day, 1, ...)`, BigQuery `DATE_ADD(..., INTERVAL 1 DAY)`
- **Safe division:** PostgreSQL `CASE WHEN ... = 0 THEN NULL ELSE ... END`, Snowflake `DIV0()`, BigQuery `SAFE_DIVIDE()`
- **Conditional count:** PostgreSQL `COUNT(CASE WHEN ... THEN 1 END)`, Snowflake `COUNT_IF()`, BigQuery `COUNTIF()`

### Composed templates

Some tests compose multiple templates together. For example, `test_is_yesterday` builds a CTE with timestamp literals, then filters with `get_is_yesterday_expression_template`. If this test fails, check that `literal_datetime_template`, `alias_field_template`, `build_cte_template`, and `union_queries_template` all work correctly first.

### Boolean flags

Four methods return `"true"` or `"false"` as plain strings (not Jinja templates):
- `supports_literal_select_template`
- `supports_literal_group_by_template`
- `supports_group_by_on_subquery_template`
- `parses_timestamp_with_trailing_text_template`

## capabilities.json

After each test run, the test suite generates `output/<name>/capabilities.json`. This file contains:

- **`templates`**: Pass/fail/skip status for every `@pytest.mark.template(func="...")` method
- **`capabilities`**: Boolean flags derived from `@pytest.mark.capability(...)` tests (e.g., `supports_volume_rows`, `supports_freshness`)
- **`metrics`**: Which Monte Carlo metrics your integration supports, derived from template pass/fail status via `qlbase_method_metrics_mapping.csv`

Do **not** edit this file manually — it is auto-generated. Use it to track your progress and see which methods still need implementation.

## Debug Workflow

1. Run the failing test with `-v` for verbose output
2. Read the error message — it tells you which template failed and why
3. Check the method's docstring in `integrations/_base/integration.py` for examples
4. If the template renders but SQL fails, try the rendered SQL directly in your database client
5. Fix the template, re-run the single test
6. Once the single test passes, re-run the full phase gate
