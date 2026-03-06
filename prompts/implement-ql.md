---
name: implement-ql
description: >
  Guide for implementing Phase 4 query language templates (~94 methods) in the custom-integration-setup repo.
  Use when implementing QueryLanguageTemplates methods, working through any of the 13 subsections, or
  when running query language tests. Requires Phases 1-3 to already pass. Start with Core Query Building (#1).
---

# Phase 4: Implement Query Language (QueryLanguageTemplates)

Implement ~94 Jinja template methods in `QueryLanguageTemplates`. This is the bulk of the work. Each method returns a Jinja template string. Read the docstring in `integrations/_base/integration.py` for each method before implementing — it contains dialect-specific examples.

## Prerequisites

- Phase 1 (connection) gate passes.
- Phases 2–3 gate tests pass. In particular, `get_count_all_expression_template` must work since most QL tests depend on it.
  ```bash
  INTEGRATION=$ARGUMENTS pytest -m metadata && INTEGRATION=$ARGUMENTS pytest -m custom_monitors
  ```
- **Never read `.env` files or files containing credentials.**

`$ARGUMENTS` is the integration name (auto-detected if only one integration exists in `integrations/`).

---

## Implementation Order (Start Here)

> **CRITICAL: Implement Core Query Building (#1) first.** Nearly every test uses `make_data_source()`, which depends on `build_cte_template`, `add_select_clause_template`, `add_from_clause_template`, `union_queries_template`, and `alias_field_template`. If these are wrong, all other QL tests will fail.
>
> After Core Query Building, prioritize in this order for maximum test coverage:
> 1. Core Query Building (#1) — unlocks all other tests
> 2. String and Literal Handling (#2) — `escape_field_name_template` and `literal_datetime_template` are used across many tests
> 3. Aggregation Functions (#8) — `get_count_all_expression_template` is critical; implement this section early
> 4. Comparison Operators (#6) — straightforward and unblock many other tests
> 5. Remaining sections in any order

---

## Table of Contents

| # | Subsection | Methods | Test File | Pytest Command |
|---|---|---|---|---|
| 1 | [Core Query Building](#1-core-query-building) | 13 | `test_ql_query_building.py` | `pytest tests/test_ql_query_building.py` |
| 2 | [String and Literal Handling](#2-string-and-literal-handling) | 7 | `test_ql_query_building.py` | (same file) |
| 3 | [Type Casting](#3-type-casting) | 14 | `test_ql_type_casting.py` | `pytest tests/test_ql_type_casting.py` |
| 4 | [Date/Time Functions](#4-datetime-functions) | 20 | `test_ql_datetime.py` | `pytest tests/test_ql_datetime.py` |
| 5 | [Dialect Capability Flags](#5-dialect-capability-flags) | 4 | `test_ql_query_building.py` / `test_ql_math.py` / `test_ql_advanced.py` | (spread across files) |
| 6 | [Comparison Operators](#6-comparison-operators) | 7 | `test_ql_comparison.py` | `pytest tests/test_ql_comparison.py` |
| 7 | [Null and NaN Handling](#7-null-and-nan-handling) | 4 | `test_ql_comparison.py` / `test_ql_null_nan.py` | `pytest tests/test_ql_null_nan.py` |
| 8 | [Aggregation Functions](#8-aggregation-functions) | 10 | `test_ql_aggregation.py` | `pytest tests/test_ql_aggregation.py` |
| 9 | [String Functions](#9-string-functions) | 5 | `test_ql_string_ops.py` | `pytest tests/test_ql_string_ops.py` |
| 10 | [Math Functions](#10-math-functions) | 2 | `test_ql_math.py` | `pytest tests/test_ql_math.py` |
| 11 | [Array and Timestamp Validation](#11-array-and-timestamp-validation) | 6 | `test_ql_advanced.py` | `pytest tests/test_ql_advanced.py` |
| 12 | [RCA and Advanced Functions](#12-rca-and-advanced-functions) | 2 | `test_ql_advanced.py` | (same file) |
| 13 | [Field Operations](#13-field-operations) | 1 | `test_ql_query_building.py` | (same file) |

---

## 1. Core Query Building

**Test file:** `tests/test_ql_query_building.py` | **Run:** `INTEGRATION=<name> pytest tests/test_ql_query_building.py`

| Method | Jinja Variables | Test |
|---|---|---|
| `build_cte_template` | `alias`, `query` | `test_select_from_cte` |
| `add_select_clause_template` | `fields` | `test_select_from_cte` |
| `add_from_clause_template` | `table` | `test_select_from_cte` |
| `union_queries_template` | `queries` (list) | `test_union_all` |
| `alias_field_template` | `field`, `alias` | `test_escape_field_name` |
| `all_fields_expression_template` | _(none)_ | `test_all_fields_expression` |
| `escape_field_name_template` | `field_name` | `test_escape_field_name` |
| `get_table_identifier_template` | `database`, `schema`, `table` | `test_get_table_identifier` |
| `get_arbitrary_where_clause_template` | _(none)_ | `test_arbitrary_where_clause` |
| `ascending_order_template` | `field` | `test_ordering` |
| `descending_order_template` | `field` | `test_ordering` |
| `get_case_when_func_template` | `condition`, `true_value`, `false_value` | `test_case_when` |
| `negate_expression_template` | `expression` | `test_negate_expression` |

**Key test expectations:**
- `test_select_from_cte`: CTE with 2 rows `[{col_a:1, col_b:"hello"}, {col_a:2, col_b:"world"}]`, SELECT ordered by col_a ASC → rows[0][0]==1, rows[1][0]==2
- `test_union_all`: 5-row CTE via union, COUNT(*) == 5
- `test_ordering`: CTE [3,1,2], ASC → [1,2,3], DESC → [3,2,1]
- `test_get_table_identifier`: Result contains "my_db", "my_schema", "my_table"

---

## 2. String and Literal Handling

**Test file:** `tests/test_ql_query_building.py` | **Run:** `INTEGRATION=<name> pytest tests/test_ql_query_building.py`

| Method | Jinja Variables | Test |
|---|---|---|
| `escape_string_template` | `value` | `test_string_literal_with_escaping` |
| `string_literal_template` | `value` | `test_string_literal_with_escaping` |
| `literal_value_template` | `value` | `test_literal_value_int` (in type_casting) |
| `literal_datetime_template` | `value` (datetime) | `test_is_yesterday` (in datetime) |
| `literal_time_of_day_template` | `value` | `test_literal_time_of_day` (in string_ops) |
| `literal_regex_template` | `value` | `test_regexp_match` (in string_ops) |
| `literal_table_from_value_list_template` | `values` (list) | `test_literal_table_from_value_list` |

**Key test expectations:**
- `test_string_literal_with_escaping`: escape then wrap `"it's a test"` → result == `"it's a test"`

---

## 3. Type Casting

**Test file:** `tests/test_ql_type_casting.py` | **Run:** `INTEGRATION=<name> pytest tests/test_ql_type_casting.py`

| Method | Jinja Variables | Test |
|---|---|---|
| `get_casting_to_numeric_expression_template` | `field` | `test_cast_to_numeric` |
| `cast_to_string_func_template` | `field` | `test_cast_to_string` |
| `get_casting_to_decimal_expression_template` | `field` | `test_cast_to_decimal` |
| `default_cast_to_timestamp_func_template` | `field` | `test_cast_to_timestamp` |
| `cast_string_to_timestamp_template` | `field` | `test_cast_string_to_timestamp` |
| `cast_numeric_to_timestamp_template` | `field` | `test_cast_numeric_to_timestamp` |
| `cast_date_to_timestamp_template` | `field` | `test_cast_date_to_timestamp` |
| `cast_default_to_timestamp_template` | `field` | `test_cast_default_to_timestamp` |
| `cast_timestamp_to_date_template` | `field` | `test_cast_timestamp_to_date` |
| `cast_timestamp_to_timestamp_ntz_template` | `field` | `test_cast_timestamp_to_timestamp_ntz` |
| `cast_timestamp_to_timestamp_tz_template` | `field` | `test_cast_timestamp_to_timestamp_tz` |
| `cast_to_timestamp_with_tz_template` | _(none)_ | `test_cast_to_timestamp_with_tz` |
| `cast_to_timestamp_without_tz_template` | _(none)_ | `test_cast_to_timestamp_without_tz` |
| `date_literal_template` | `value` (date) | `test_date_literal` (in datetime) |

**Key test expectations:**
- `test_cast_to_numeric`: CAST('42.5') → 42.5
- `test_cast_to_string`: CAST(123) → "123"
- `test_cast_to_decimal`: CAST('3.14159') → ≈3.14159
- Timestamp casts: verify result string contains expected date parts ("2024", "15", etc.)
- `test_cast_to_timestamp_with_tz` / `without_tz`: just verify non-empty string returned

---

## 4. Date/Time Functions

**Test file:** `tests/test_ql_datetime.py` | **Run:** `INTEGRATION=<name> pytest tests/test_ql_datetime.py`

| Method | Jinja Variables | Test |
|---|---|---|
| `current_timestamp_func_template` | _(none)_ | `test_current_timestamp` |
| `current_date_func_template` | _(none)_ | `test_current_date` |
| `convert_to_utc_template` | `field` | `test_convert_to_utc` |
| `add_days_func_template` | `field`, `days` | `test_add_days` |
| `add_days_timestamp_func_template` | `field`, `days` | `test_add_days_timestamp` |
| `add_hours_timestamp_func_template` | `field`, `hours` | `test_add_hours_timestamp` |
| `time_truncate_func_template` | `field`, `truncation` | `test_time_truncate` |
| `truncate_to_day_template` | `field` | `test_truncate_to_day` |
| `truncate_to_hour_template` | `field` | `test_truncate_to_hour` |
| `truncate_to_week_template` | `field` | `test_truncate_to_week` |
| `truncate_to_month_template` | `field` | `test_truncate_to_month` |
| `truncate_to_year_template` | `field` | `test_truncate_to_year` |
| `get_is_yesterday_expression_template` | `field` | `test_is_yesterday` |
| `get_in_past_days_expression_template` | `field`, `days` | `test_in_past_days` |
| `get_in_past_hours_expression_template` | `field`, `hours` | `test_in_past_hours` |
| `get_in_past_calendar_week_expression_template` | `field`, `weeks` | `test_in_past_calendar_week` |
| `get_in_past_calendar_month_expression_template` | `field`, `months` | `test_in_past_calendar_month` |
| `get_date_diff_func_template` | `field1`, `field2`, `unit` | `test_date_diff` |
| `get_days_of_week_expression_template` | `field` | `test_days_of_week` |
| `convert_to_unix_timestamp_func_template` | `field` | `test_current_timestamp` |

Also tested in this file: `utc_literal_template` (no variables, returns UTC timezone literal string).

**Key test expectations:**
- `test_current_timestamp`: epoch seconds within 120s of Python's `datetime.now(UTC)`
- `test_is_yesterday`: CTE with yesterday_noon + today_noon, COUNT WHERE is_yesterday → 1
- `test_in_past_days`: CTE with 2_days_ago + 30_days_ago, past 7 days → 1
- `test_date_diff`: diff between Jan 1 and Jan 11 → abs(result) == 10
- Truncation tests: verify time portion is removed from result string

---

## 5. Dialect Capability Flags

These return `"true"` or `"false"` (as strings). No Jinja variables.

| Method | Test File | Test |
|---|---|---|
| `supports_literal_select_template` | `test_ql_math.py` | `test_absolute_value` |
| `supports_literal_group_by_template` | `test_ql_query_building.py` | `test_supports_literal_group_by` |
| `supports_group_by_on_subquery_template` | `test_ql_query_building.py` | `test_supports_group_by_on_subquery` |
| `parses_timestamp_with_trailing_text_template` | `test_ql_advanced.py` | `test_parses_timestamp_with_trailing_text` |

Most databases return `"true"` for the first three. `parses_timestamp_with_trailing_text_template` is database-specific:
- Snowflake: `"true"` (ignores trailing text in timestamp strings)
- PostgreSQL: `"false"` (strict parsing)
- BigQuery: `"false"`
- SQLite: `"true"`

---

## 6. Comparison Operators

**Test file:** `tests/test_ql_comparison.py` | **Run:** `INTEGRATION=<name> pytest tests/test_ql_comparison.py`

| Method | Jinja Variables | Test |
|---|---|---|
| `get_is_eq_expression_template` | `field1`, `field2` | `test_equality` |
| `get_is_gt_expression_template` | `field1`, `field2` | `test_gt_and_lt` |
| `get_is_gte_expression_template` | `field1`, `field2` | `test_gte_and_lte` |
| `get_is_lt_expression_template` | `field1`, `field2` | `test_gt_and_lt` |
| `get_is_lte_expression_template` | `field1`, `field2` | `test_gte_and_lte` |
| `get_is_inside_range_expression_template` | `field`, `lower`, `upper` | `test_inside_range` |
| `get_is_outside_range_expression_template` | `field`, `lower`, `upper` | `test_outside_range` |

**Key test expectations:**
- `test_equality`: CTE [{x:10,y:10},{x:10,y:20}], COUNT WHERE x=y → 1
- `test_gt_and_lt`: CTE [5,10,15], COUNT WHERE >8 → 2, <8 → 1
- `test_inside_range`: CTE [1,5,10,15], range 5–10 → 2 (inclusive)
- `test_outside_range`: same data, outside 5–10 → 2

---

## 7. Null and NaN Handling

**Test files:** `tests/test_ql_comparison.py`, `tests/test_ql_null_nan.py` | **Run:** `INTEGRATION=<name> pytest tests/test_ql_null_nan.py`

| Method | Jinja Variables | Test |
|---|---|---|
| `is_null_template` | `field` | `test_null_checks` (in comparison) |
| `is_not_null_template` | `field` | `test_null_checks` (in comparison) |
| `nan_expr_template` | _(none)_ | `test_isnan` |
| `get_isnan_expression_template` | `field` | `test_isnan` |

**Key test expectations:**
- `test_null_checks`: CTE [1,NULL,3], IS NULL → 1, IS NOT NULL → 2
- `test_isnan`: NaN literal via `nan_expr_template`, check with `get_isnan_expression_template` → CASE returns 1

**NaN handling is highly dialect-specific:**
- PostgreSQL: `'NaN'::float` / `CASE WHEN {{ field }} != {{ field }} THEN 1 END` (NaN != NaN in IEEE 754)
- Snowflake: `'NaN'::FLOAT` / `IS_NAN({{ field }})`
- BigQuery: `CAST('NaN' AS FLOAT64)` / `IS_NAN({{ field }})`
- SQLite: no native NaN support — may need a workaround

---

## 8. Aggregation Functions

**Test file:** `tests/test_ql_aggregation.py` | **Run:** `INTEGRATION=<name> pytest tests/test_ql_aggregation.py`

| Method | Jinja Variables | Test |
|---|---|---|
| `get_avg_function_template` | `field` | `test_avg` |
| `get_stddev_function_template` | `field` | `test_stddev` |
| `get_distinct_count_func_template` | `field` | `test_distinct_count` |
| `get_distinct_func_template` | `field` | `test_distinct_func` |
| `get_safe_divide_template` | `numerator`, `denominator` | `test_safe_divide` |
| `get_conditional_count_expression_template` | `condition` | `test_conditional_count` |
| `get_approx_quantiles_func_template` | `field`, `quantiles`, `index` | `test_approx_quantiles` |
| `get_approx_percentile_func_template` | `field`, `percentile` | `test_approx_percentile` |
| `approx_distinct_func_template` | `field` | `test_approx_distinct` |
| `any_value_template` | `field` | `test_any_value` |

**Key test expectations:**
- `test_avg`: [10,20,30] → 20.0
- `test_stddev`: [10,20,30] → between 7.0 and 11.0 (sample vs population)
- `test_distinct_count`: [a,b,a,c] → 3
- `test_safe_divide`: 10/2 → 5.0; 10/0 → NULL or 0 (no error)
- `test_approx_percentile`: [1..100], median → 45–55
- `test_any_value`: [42,42,42] → 42

**Dialect-specific:**
- `get_conditional_count_expression_template`: PostgreSQL uses `COUNT(CASE WHEN {{ condition }} THEN 1 END)`, Snowflake uses `COUNT_IF({{ condition }})`, BigQuery uses `COUNTIF({{ condition }})`
- `get_safe_divide_template`: PostgreSQL uses `CASE WHEN {{ denominator }} = 0 THEN NULL ELSE {{ numerator }} / {{ denominator }} END`, Snowflake has `DIV0({{ numerator }}, {{ denominator }})`, BigQuery has `SAFE_DIVIDE({{ numerator }}, {{ denominator }})`

---

## 9. String Functions

**Test file:** `tests/test_ql_string_ops.py` | **Run:** `INTEGRATION=<name> pytest tests/test_ql_string_ops.py`

| Method | Jinja Variables | Test |
|---|---|---|
| `get_length_template` | `field` | `test_string_length` |
| `substring_func_template` | `field`, `start`, `length` | `test_substring` |
| `get_is_empty_string_expression_template` | `field` | `test_is_empty_string` |
| `get_regexp_expression_template` | `field`, `pattern` | `test_regexp_match` |
| `get_regexp_count_expression_template` | `field`, `pattern` | `test_regexp_count` |

**Key test expectations:**
- `test_string_length`: ['hello','','world!'], SUM(LENGTH) → 11
- `test_substring`: SUBSTR('abcdef', 2, 3) → 'bcd'
- `test_is_empty_string`: ['hello','','world'], COUNT WHERE empty → 1
- `test_regexp_match`: email pattern matches 2 of 3 values
- `test_regexp_count`: ^[0-9]+$ matches 2 of 3 values

**Dialect-specific regex:**
- PostgreSQL: `{{ field }} ~ {{ pattern }}`
- Snowflake: `REGEXP_LIKE({{ field }}, {{ pattern }})`
- BigQuery: `REGEXP_CONTAINS({{ field }}, {{ pattern }})`
- MySQL: `{{ field }} REGEXP {{ pattern }}`

---

## 10. Math Functions

**Test file:** `tests/test_ql_math.py` | **Run:** `INTEGRATION=<name> pytest tests/test_ql_math.py`

| Method | Jinja Variables | Test |
|---|---|---|
| `get_absolute_value_function_template` | `field` | `test_absolute_value` |
| `rand_func_template` | _(none)_ | `test_rand` |

**Key test expectations:**
- `test_absolute_value`: ABS(-5) → 5
- `test_rand`: returns a number (no error)

---

## 11. Array and Timestamp Validation

**Test file:** `tests/test_ql_advanced.py` | **Run:** `INTEGRATION=<name> pytest tests/test_ql_advanced.py`

| Method | Jinja Variables | Test |
|---|---|---|
| `array_expr_template` | `values` (list) | `test_array_length` |
| `get_array_length_func_template` | `field` | `test_array_length` |
| `get_is_timestamp_expression_template` | `field` | `test_is_timestamp_expression` |
| `get_not_is_timestamp_expression_template` | `field` | `test_not_is_timestamp` |
| `get_epoch_seconds_expression_template` | `field` | `test_epoch_seconds` |
| `get_epoch_seconds_parameter_template` | `field` | `test_epoch_seconds_parameter` |

**Key test expectations:**
- `test_array_length`: ARRAY[1,2,3] → length 3
- `test_is_timestamp_expression`: '2024-01-15 10:30:00' → is valid timestamp (CASE returns 1)
- `test_epoch_seconds`: '2024-01-01 00:00:00' → epoch ≈1704067200 (within 1 day tolerance)
- `test_epoch_seconds_parameter`: just verify non-empty result

---

## 12. RCA and Advanced Functions

**Test file:** `tests/test_ql_advanced.py` | **Run:** `INTEGRATION=<name> pytest tests/test_ql_advanced.py`

| Method | Jinja Variables | Test |
|---|---|---|
| `max_time_func_template` | `field` | `test_max_time` |
| `unpivot_template` | `query`, `columns` (list), `name_column`, `value_column` | `test_unpivot` |

**Key test expectations:**
- `test_max_time`: MAX of two timestamps → result contains "2024" and "06"
- `test_unpivot`: 1 row with 3 columns unpivoted → 3 rows

**`unpivot_template` is the most complex method.** Many databases support UNPIVOT natively (Snowflake, SQL Server). Others require a UNION ALL approach:
```sql
{% for col in columns %}
SELECT {{ name_column }} AS col_name, {{ col }} AS col_value FROM ({{ query }})
{% if not loop.last %} UNION ALL {% endif %}
{% endfor %}
```

---

## 13. Field Operations

**Test file:** `tests/test_ql_query_building.py` | **Run:** `INTEGRATION=<name> pytest tests/test_ql_query_building.py`

| Method | Jinja Variables | Test |
|---|---|---|
| `get_field_or_alias_template` | `field` | `test_field_or_alias` |

**Key test expectations:**
- `test_field_or_alias`: renders to a non-empty string

---

## Validation

Run all query language tests:
```bash
INTEGRATION=<name> pytest -m query_language
```

Or run all tests:
```bash
INTEGRATION=<name> pytest
```

Check `output/<name>/capabilities.json` for the full pass/fail report.

## Next Step

If tests fail, consult [test-and-fix.md](test-and-fix.md).

## Rules

- **Only edit `integrations/$ARGUMENTS/integration.py`.** Do not modify tests, `conftest.py`, or the plugin.
- Every template method must return a **Jinja template string**, not raw SQL or Python logic.
- Do not edit `capabilities.json` — it is auto-generated.
- Read each method's docstring in `integrations/_base/integration.py` before implementing.
