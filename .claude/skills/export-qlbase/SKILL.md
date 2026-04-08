---
name: export-qlbase
description: Convert completed pandora-setup Jinja templates into a monolith-compatible QLBase Python class
argument-hint: <connector-name> [monolith-path]
disable-model-invocation: true
---

# Export QLBase: Convert Pandora Jinja Templates → Monolith QLBase Class

You are converting a completed pandora-setup connector's Jinja template methods into a monolith-compatible `QLBase` subclass (Python methods).

## Arguments

`$ARGUMENTS` contains the connector name, and optionally a custom monolith path.

Parse like: `<connector_name> [monolith_path]`
- `connector_name` (required): e.g., `teradata`, `postgres`
- `monolith_path` (optional): defaults to `~/repos/monolith-django`

## Step 1: Read Source Files

Read these files:
1. **Pandora connector**: `connectors/$0/connector.py` — the source Jinja templates
2. **Monolith QLBase**: `$1/monolith/metrics/query_language/base.py` (or `~/repos/monolith-django/monolith/metrics/query_language/base.py` if no second arg) — the target interface
3. **Monolith PostgresQL**: same directory `postgres.py` — a reference implementation showing the pattern

Examine every method in the pandora `QueryLanguageTemplates` class and the `CustomSQLMonitorTemplates` class. Identify which ones are implemented (return a value) vs stubs (contain only `pass`). Only convert implemented methods.

## Step 2: Convert Templates to Python

Generate a class `<ConnectorName>QL(QLBase)` (e.g., `TeradataQL`, `PostgresQL`).

### Conversion Rules

#### Rule 1: Strip `_template` suffix
`get_avg_function_template` → `get_avg_function`

#### Rule 2: Match the monolith method signature
Look up each method in `base.py` to get the correct signature. The monolith signature is authoritative.

**Expression-template methods** (no params in monolith, return `{x}`, `{y}` placeholder strings):
```python
# Pandora:  def get_is_eq_expression_template(self): return "{{ field1 }} = {{ field2 }}"
# Monolith: def get_is_eq_expression(self) -> str: return "{x} = {y}"
```
For these, map the first Jinja variable to `{x}`, the second to `{y}`.

**Parameterized methods** (take params in monolith, return f-strings):
```python
# Pandora:  def get_safe_divide_template(self): return "COALESCE({{ dividend }} / NULLIF({{ divisor }}, 0), 0)"
# Monolith: def get_safe_divide(self, dividend: str, divisor: str) -> str
# Output:   def get_safe_divide(self, dividend: str, divisor: str) -> str:
#               return f"COALESCE({dividend} / NULLIF({divisor}, 0), 0)"
```

#### Rule 3: Boolean capability flags
```python
# Pandora:  def supports_literal_select_template(self): return "true"
# Monolith: def supports_literal_select(self) -> bool: return True
```
Convert string `"true"` → `True`, `"false"` → `False`.

#### Rule 4: Jinja filters → Python code
- `{{ value | replace("'", "''") }}` → implement as Python: `return string.replace("'", "''")`
- `{{ queries | join(' UNION ALL ') }}` → `return " UNION ALL ".join(queries)`
- `{{ value.strftime('%Y-%m-%d') }}` → `return f"'{value.strftime('%Y-%m-%d')}'"` (keep Python method calls)

#### Rule 5: Timestamp casting methods → dict properties
Pandora has individual methods; monolith uses dict properties looked up by field type.

Map these pandora methods into the `_cast_to_timestamp_functions` property dict:
| Pandora method | Dict key |
|---|---|
| `cast_string_to_timestamp_template` | `"TEXT"`, `"VARCHAR"`, `"STRING"` (choose based on SQL dialect) |
| `cast_numeric_to_timestamp_template` | `"INTEGER"`, `"BIGINT"`, `"NUMBER"` |
| `cast_date_to_timestamp_template` | `"DATE"` |
| `cast_default_to_timestamp_template` | Used as the default (or for `"TIMESTAMP"`) |

Map these pandora methods into `_cast_timestamp_to_field` property (defaultdict):
| Pandora method | Dict key |
|---|---|
| `cast_timestamp_to_date_template` | `"DATE"` |
| Default (identity) | `defaultdict(lambda: "{x}")` |

Map these pandora methods into string properties:
| Pandora method | Monolith property |
|---|---|
| `cast_timestamp_to_timestamp_ntz_template` | `_cast_to_timestamp_without_tz` |
| `cast_timestamp_to_timestamp_tz_template` | `_cast_to_timestamp_with_tz` |

#### Rule 6: Truncation methods → dict property
Pandora has `truncate_to_day_template`, `truncate_to_hour_template`, etc. and `time_truncate_func_template`.

In the monolith, there's a `_truncate_functions` property dict mapping field types to format strings:
```python
_TRUNCATE_FUNC = "DATE_TRUNC('{interval}', {x})"
_TIME_TRUNCATE_FUNCTIONS = {
    "DATE": _TRUNCATE_FUNC,
    "TIMESTAMP": _TRUNCATE_FUNC,
    ...
}
```

Examine the pandora `time_truncate_func_template` to determine the base truncation pattern, then populate the dict. The individual `truncate_to_*` methods in pandora are tested but don't need separate methods in the monolith — they're handled by passing different `interval` values to the truncation function.

#### Rule 7: Methods with different signatures
Some methods have signature differences between pandora and monolith. Always use the monolith signature:

- `get_case_when_func`: Pandora takes `condition, true_value, false_value`. Monolith takes `conditions_and_results: list[tuple[str, str]], else_result: str | None`. Use monolith signature.
- `get_avg_function`: Pandora has no params. Monolith takes optional `field_type`.
- `unpivot`: Pandora takes `value_column, name_column, column_list, from_table`. Monolith takes same but named `_from`.
- `get_days_of_week_expression`: Pandora takes `days` as Jinja list. Monolith takes `days: list[str]`.
- `get_regexp_expression` / `get_regexp_count_expression`: Monolith takes `regexp: str, case_insensitive: bool`.
- `add_hours_timestamp_func`: Monolith adds optional `time_field_name` param.
- `approx_distinct_func`: Monolith takes `field_name: str, field_type: str | None`.
- `escape_field_name`: Monolith takes `field_name: str, from_original_name: bool = False`.
- `get_epoch_seconds_expression`: Monolith takes `current_time: bool = False`.

#### Rule 8: CustomSQLMonitorTemplates methods
These pandora methods map to QLBase/QLMinimal methods:
- `transform_into_count_query_template` → `transform_into_count_query`
- `add_row_limit_template` → `add_row_limit`
- `get_count_all_expression_template` → `get_count_all_expression`

Only override if the pandora implementation differs from the QLBase default.

#### Rule 9: Methods with no monolith equivalent
Some pandora methods don't have direct monolith counterparts. Add them as comments:
- `array_expr_template` — no equivalent in QLBase
- `nan_expr_template` — related to `get_isnan_expression` but different
- `parses_timestamp_with_trailing_text_template` — no equivalent
- `convert_to_utc_template` — exists but needs manual work (monolith version takes `field_type` param)

#### Rule 10: `get_table_identifier`
Monolith's `get_table_identifier` takes a `ParsedMCON` object, not template variables. Add a TODO:
```python
def get_table_identifier(self, mcon: ParsedMCON) -> str:
    # TODO: Adapt from pandora template which used database/schema/table variables
    # Pandora template: "{{ database }}.{{ schema }}.{{ table }}"
    full_table_id = mcon.object_id.replace(":", ".")
    table_parts = [self.escape_field_name(x) for x in full_table_id.split(".")]
    return ".".join(table_parts)
```

## Step 3: Write the Output

Write the generated class to `output/$0/qlbase.py`.

### File structure:
```python
"""
Auto-generated QLBase class for <connector_name>.

Converted from pandora-setup Jinja templates to monolith-compatible Python.
Review TODOs before using in production.
"""
import abc
import collections
from collections import defaultdict
from datetime import datetime

from montecarlodata_common.mcon import ParsedMCON

from monolith.metrics.query_language.base import QLBase
from monolith.metrics.query_language.fields import FieldsUtil

class <ConnectorName>QL(QLBase):
    # ... class-level constants (truncation dicts, cast dicts) ...
    # ... property implementations ...
    # ... method implementations ...
```

### Ordering
Group methods in the same order as QLBase:
1. Class-level constants (`_TRUNCATE_FUNC`, `_TIME_TRUNCATE_FUNCTIONS`, etc.)
2. Abstract property implementations (`_truncate_functions`, `_cast_to_timestamp_functions`, etc.)
3. Core methods (in the order they appear in QLBase)
4. TODO comments for methods needing manual adaptation

## Step 4: Summary

After generating, print a summary:
- Total methods converted
- Methods skipped (stubs in pandora)
- Methods needing manual review (TODOs)
- Reminder to compare against monolith reference implementations and run monolith tests
