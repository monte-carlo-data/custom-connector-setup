"""
Auto-generated QLBase class for ms_fabric.

Converted from pandora-setup Jinja templates to monolith-compatible Python.
Review TODOs before using in production.
"""
import collections
from collections import defaultdict
from datetime import datetime

from montecarlodata_common.mcon import ParsedMCON

from monolith.metrics.query_language.base import QLBase


class MsFabricQL(QLBase):
    _TRUNCATE_FUNC = "DATETRUNC({interval}, {x})"
    _TIME_TRUNCATE_FUNCTIONS = {
        "DATE": _TRUNCATE_FUNC,
        "DATETIME": _TRUNCATE_FUNC,
        "DATETIME2": _TRUNCATE_FUNC,
        "DATETIMEOFFSET": _TRUNCATE_FUNC,
        "TIMESTAMP": _TRUNCATE_FUNC,
        "TIMESTAMP WITHOUT TIME ZONE": _TRUNCATE_FUNC,
        "TIMESTAMP WITH TIME ZONE": _TRUNCATE_FUNC,
    }

    _CAST_TO_TIMESTAMP_FUNCTIONS = {
        "DATE": "CAST({x} AS DATETIME2)",
        "TEXT": "TRY_CAST({x} AS DATETIME2)",
        "VARCHAR": "TRY_CAST({x} AS DATETIME2)",
        "NVARCHAR": "TRY_CAST({x} AS DATETIME2)",
        "STRING": "TRY_CAST({x} AS DATETIME2)",
        "INTEGER": "DATEADD(SECOND, {x}, CAST('1970-01-01' AS DATETIME2))",
        "BIGINT": "DATEADD(SECOND, {x}, CAST('1970-01-01' AS DATETIME2))",
        "NUMBER": "DATEADD(SECOND, {x}, CAST('1970-01-01' AS DATETIME2))",
        "TIMESTAMP": "TRY_CAST({x} AS DATETIME2)",
        "DATETIME2": "{x}",
        "DATETIMEOFFSET": "CAST({x} AS DATETIME2)",
    }

    _CAST_TIMESTAMP_TO_FIELD = collections.defaultdict(
        lambda: "{x}",
        {
            "DATE": "CAST({x} AS DATE)",
        },
    )

    # -----------------------------------------------------------------------
    # Abstract property implementations
    # -----------------------------------------------------------------------

    @property
    def _truncate_functions(self) -> dict:
        return self._TIME_TRUNCATE_FUNCTIONS

    @property
    def _cast_to_timestamp_functions(self) -> dict:
        return self._CAST_TO_TIMESTAMP_FUNCTIONS

    @property
    def _cast_to_timestamp_with_tz(self) -> str:
        return "CAST({x} AS DATETIMEOFFSET)"

    @property
    def _cast_to_timestamp_without_tz(self) -> str:
        return "CAST({x} AS DATETIME2)"

    @property
    def _cast_timestamp_to_field(self) -> defaultdict:
        return self._CAST_TIMESTAMP_TO_FIELD

    # -----------------------------------------------------------------------
    # Core methods
    # -----------------------------------------------------------------------

    def add_row_limit(self, query: str, limit: int) -> str:
        return f"SELECT TOP {int(limit)} * FROM (\n{query.strip(';')}\n) AS _row_limited"

    def negate_expression(self, query: str) -> str:
        if query == "TRUE":
            return "1 = 0"
        elif query == "FALSE":
            return "1 = 1"
        return f"NOT {query}"

    def get_arbitrary_where_clause(self) -> str:
        return "1=1"

    def escape_field_name(self, field_name: str, from_original_name: bool = False) -> str:
        return f"[{field_name}]"

    def get_table_identifier(self, mcon: ParsedMCON) -> str:
        # TODO: Adapt from pandora template which used database/schema/table variables
        # Pandora template: "{{ database }}.{{ schema }}.{{ table }}"
        full_table_id = mcon.object_id.replace(":", ".")
        table_parts = [self.escape_field_name(x) for x in full_table_id.split(".")]
        return ".".join(table_parts)

    def convert_to_utc(self, field: str, field_type: str | None = None) -> str:
        # TODO: monolith version takes field_type; pandora template used field only.
        # Pandora template: SWITCHOFFSET(CAST({{ field }} AS DATETIMEOFFSET), '+00:00')
        return f"SWITCHOFFSET(CAST({field} AS DATETIMEOFFSET), '+00:00')"

    def get_casting_to_numeric_expression(self, expression: str) -> str:
        return f"CAST({expression} AS FLOAT)"

    def get_casting_to_decimal_expression(self, expression: str) -> str:
        return f"CAST({expression} AS DECIMAL(38, 10))"

    def current_date_func(self) -> str:
        return "CAST(GETUTCDATE() AS DATE)"

    def current_timestamp_func(self) -> str:
        return "GETUTCDATE()"

    def default_cast_to_timestamp_func(self, expr: str) -> str:
        return f"CAST({expr} AS DATETIME2)"

    def add_days_func(self, date_expr: str, days: int | str) -> str:
        return f"DATEADD(day, {days}, {date_expr})"

    def add_days_timestamp_func(self, date_expr: str, days: int | str) -> str:
        return f"DATEADD(day, {days}, {date_expr})"

    def add_hours_timestamp_func(
        self,
        date_expr: str,
        hours: int | str,
        time_field_name: str | None = None,
    ) -> str:
        return f"DATEADD(hour, {hours}, {date_expr})"

    def approx_distinct_func(self, field_name: str, field_type: str | None = None) -> str:
        return f"APPROX_COUNT_DISTINCT({field_name})"

    def convert_to_unix_timestamp_func(self, date_expr: str) -> str:
        return f"DATEDIFF_BIG(SECOND, '1970-01-01', {date_expr})"

    def cast_to_string_func(self, expr: str, field_type: str | None = None) -> str:
        return f"CAST({expr} AS NVARCHAR(MAX))"

    def rand_func(self) -> str:
        return "ABS(CHECKSUM(NEWID())) % 1000000000 * 1.0 / 1000000000"

    def max_time_func(self, field: str) -> str:
        return f"MAX({field})"

    def get_conditional_count_expression(self, expression: str) -> str:
        return f"COUNT(CASE WHEN {expression} THEN 1 END)"

    def get_field_or_alias(self, field: str, alias: str) -> str:
        return alias

    def get_approx_quantiles_func(self, expr: str, num_of_quantiles: int) -> str:
        # T-SQL APPROX_PERCENTILE_CONT returns a single value; simulate quantiles
        percentiles = [
            "APPROX_PERCENTILE_CONT({:.2f}) WITHIN GROUP (ORDER BY {})".format(
                float(i) / num_of_quantiles, expr
            )
            for i in range(num_of_quantiles + 1)
        ]
        return ", ".join(percentiles)

    def get_approx_percentile_func(self, expr: str, percentile: float) -> str:
        return f"APPROX_PERCENTILE_CONT({percentile:.2f}) WITHIN GROUP (ORDER BY {expr})"

    def get_stddev_function(self) -> str:
        return "STDEV({x})"

    def get_avg_function(self, field_type: str | None = None) -> str:
        return "AVG({x})"

    def get_regexp_count_expression(self, regexp: str, case_insensitive: bool = True) -> str:
        raise NotImplementedError("T-SQL does not support native regex count")

    def get_regexp_expression(self, regexp: str, case_insensitive: bool = True) -> str:
        raise NotImplementedError("T-SQL does not support native regex matching")

    def get_array_length_func(self) -> str:
        raise NotImplementedError("T-SQL does not support native array types")

    def get_isnan_expression(self) -> str:
        raise NotImplementedError("T-SQL has no NaN concept")

    def get_is_yesterday_expression(self) -> str:
        return "{x} >= DATEADD(day, -1, CAST(GETUTCDATE() AS DATE)) AND {x} < CAST(GETUTCDATE() AS DATE)"

    def get_in_past_days_expression(self, days: int | str) -> str:
        return f"{{x}} >= DATEADD(day, -{days}, GETUTCDATE())"

    def get_in_past_hours_expression(self, hours: int | str) -> str:
        return f"{{x}} >= DATEADD(hour, -{hours}, GETUTCDATE())"

    def get_in_past_calendar_week_expression(self) -> str:
        return "DATETRUNC(week, CAST({x} AS DATE)) = DATETRUNC(week, CAST(GETUTCDATE() AS DATE))"

    def get_in_past_calendar_month_expression(self) -> str:
        return "DATETRUNC(month, CAST({x} AS DATE)) = DATETRUNC(month, CAST(GETUTCDATE() AS DATE))"

    def get_days_of_week_expression(self, days: list[str]) -> str:
        _DAY_OF_WEEK = {
            "SUNDAY": 1,
            "MONDAY": 2,
            "TUESDAY": 3,
            "WEDNESDAY": 4,
            "THURSDAY": 5,
            "FRIDAY": 6,
            "SATURDAY": 7,
        }
        day_counts = ", ".join([str(_DAY_OF_WEEK[day.upper()]) for day in days])
        return f"DATEPART(WEEKDAY, {{x}}) IN ({day_counts})"

    def get_is_timestamp_expression(self) -> str:
        return "TRY_CAST({x} AS DATETIME2) IS NOT NULL"

    def get_not_is_timestamp_expression(self) -> str:
        return "TRY_CAST({x} AS DATETIME2) IS NULL"

    def get_epoch_seconds_expression(self, current_time: bool = False) -> str:
        if current_time:
            return "DATEDIFF_BIG(SECOND, '1970-01-01', GETUTCDATE())"
        return "DATEDIFF_BIG(SECOND, '1970-01-01', {x})"

    def get_date_diff_func(self, date_part: str, date_expr1: str, date_expr2: str) -> str:
        return f"DATEDIFF({date_part}, {date_expr1}, {date_expr2})"

    def unpivot(
        self,
        value_column: str,
        name_column: str,
        column_list: list[str],
        _from: str,
    ) -> str:
        cols = ", ".join(column_list)
        return (
            f"SELECT {name_column}, {value_column} FROM ({_from}) AS _src "
            f"UNPIVOT ({value_column} FOR {name_column} IN ({cols})) AS _unpivoted"
        )

    def any_value(self, col_name: str) -> str:
        return f"MIN({col_name})"

    def get_safe_divide(self, dividend: str, divisor: str) -> str:
        return f"{dividend} / NULLIF({divisor}, 0)"

    def get_length(self) -> str:
        return "LEN({x})"

    def substring_func(self, field: str, start_pos: int, length: int | None = None) -> str:
        if length is None:
            return f"SUBSTRING({field}, {start_pos}, LEN({field}))"
        return f"SUBSTRING({field}, {start_pos}, {length})"

    def literal_time_of_day(self, value: str) -> str:
        return f"CAST('{value}' AS TIME)"

    def literal_datetime(self, date_time_value: datetime) -> str:
        return f"CONVERT(DATETIME2, '{date_time_value.strftime('%Y-%m-%d %H:%M:%S')}')"

    def escape_string(self, string: str) -> str:
        return string.replace("'", "''")
