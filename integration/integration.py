from typing import Any, List


class BaseIntegration:
    ########################################
    # Connection Related Methods
    ########################################
    def create_connection(self) -> Any:
        pass

    def create_cursor(self) -> Any:
        pass

    def close_connection(self):
        pass

    ########################################
    # Execution Related Methods
    ########################################
    def execute_query(self, query: str) -> None:
        pass

    def fetch_all_results(self) -> List[Any]:
        pass


class MetadataQueryTemplates:
    ########################################
    # Metadata Job Related Methods
    ########################################
    def get_databases_query_template(self) -> str:
        """Jinja template that returns a list of accessible databases.

        Jinja variables:
            None

        Examples:
            Snowflake: "SHOW DATABASES"
            PostgreSQL: "SELECT datname FROM pg_database WHERE datistemplate = false"

        Tier: core
        Enables: database discovery
        """
        pass

    def get_schemas_query_template(self) -> str:
        """Jinja template that returns schemas for a given database.

        Jinja variables:
            database_name (str): Name of the database to list schemas for.

        Examples:
            Snowflake: "SHOW SCHEMAS IN DATABASE {{ database_name }}"
            PostgreSQL: "SELECT schema_name FROM information_schema.schemata WHERE catalog_name = '{{ database_name }}'"

        Tier: core
        Enables: schema discovery
        """
        pass

    def get_tables_query_template(self) -> str:
        """Jinja template that returns tables and views for given schemas.

        Jinja variables:
            database_name (str): Name of the database.
            schemas (str): Comma-separated, quoted schema names.
            offset (int): Row offset for pagination.
            limit (int): Maximum rows to return.

        Returns columns: database_name, schema_name, table_name, table_type,
            row_count (optional), byte_count (optional), last_update_time (optional),
            view_query (optional)

        Tier: core
        Enables: table discovery, volume rows, volume bytes, freshness
        """
        pass

    def get_columns_query_template(self) -> str:
        """Jinja template that returns column metadata for given tables.

        Jinja variables:
            database_name (str): Name of the database.
            tables (str): Comma-separated, quoted full table identifiers.

        Returns columns: full_table_id, column_name, column_type

        Tier: core
        Enables: schema collection
        """
        pass


class QueryLogCollectionTemplates:
    ########################################
    # Query Log Job Related Methods
    ########################################
    def get_query_logs_query_template(self) -> str:
        """Jinja template that returns query logs within a time range.

        Jinja variables:
            start_time (datetime): Start of the time range.
            end_time (datetime): End of the time range.

        Tier: standard
        Enables: query log collection, lineage, field lineage
        """
        pass


class CustomSQLMonitorTemplates:
    ###################################################
    # Custom SQL Monitors Related Methods
    ###################################################
    def transform_into_count_query_template(self) -> str:
        """Jinja template that wraps a query in a COUNT(*) outer query.

        Jinja variables:
            query (str): The inner SQL query to count rows from.

        Examples:
            Snowflake/PostgreSQL: "SELECT COUNT(*) FROM ({{ query }}) AS count_query"
            BigQuery: "SELECT COUNT(*) FROM ({{ query }})"

        Tier: core
        Enables: custom SQL monitor row counting
        """
        pass

    def add_row_limit_template(self) -> str:
        """Jinja template that adds a row limit to a query.

        Jinja variables:
            query (str): The SQL query to limit.
            limit (int): Maximum number of rows.

        Examples:
            Snowflake/PostgreSQL: "{{ query }} LIMIT {{ limit }}"
            SQL Server: "SELECT TOP {{ limit }} * FROM ({{ query }}) AS limited_query"

        Tier: core
        Enables: custom SQL monitor row limiting
        """
        pass

    def get_count_all_expression_template(self) -> str:
        """Jinja template for COUNT(*) expression.

        Jinja variables:
            None

        Examples:
            Snowflake/PostgreSQL/BigQuery: "COUNT(*)"

        Tier: core
        Enables: row_count metric, row_count_change metric
        """
        pass


###################################################
# QueryLanguage Related Methods
###################################################
class QueryLanguageTemplates:
    ###################################################
    # QueryLanguage: Core Query Building
    ###################################################
    def build_cte_template(self) -> str:
        """Jinja template for building a CTE (Common Table Expression).

        Jinja variables:
            alias (str): Name for the CTE.
            query (str): The query body of the CTE.

        Examples:
            Snowflake/PostgreSQL: "WITH {{ alias }} AS ({{ query }})"

        Tier: core
        Enables: query assembly for all monitors
        """
        pass

    def add_select_clause_template(self) -> str:
        """Jinja template for a SELECT clause.

        Jinja variables:
            fields (str): Comma-separated list of fields/expressions.

        Examples:
            Snowflake/PostgreSQL: "SELECT {{ fields }}"

        Tier: core
        Enables: query assembly for all monitors
        """
        pass

    def add_from_clause_template(self) -> str:
        """Jinja template for a FROM clause.

        Jinja variables:
            table (str): Table name or alias to select from.

        Examples:
            Snowflake/PostgreSQL: "FROM {{ table }}"

        Tier: core
        Enables: query assembly for all monitors
        """
        pass

    def union_queries_template(self) -> str:
        """Jinja template that combines multiple queries with UNION ALL.

        Jinja variables:
            queries (list[str]): List of SQL queries to union.

        Examples:
            Snowflake/PostgreSQL: "{{ queries | join(' UNION ALL ') }}"

        Tier: core
        Enables: query assembly, CTE building
        """
        pass

    def alias_field_template(self) -> str:
        """Jinja template for aliasing a field expression.

        Jinja variables:
            field (str): The expression to alias.
            alias (str): The alias name.

        Examples:
            Snowflake/PostgreSQL: "{{ field }} AS {{ alias }}"

        Tier: core
        Enables: query assembly for all monitors
        """
        pass

    def all_fields_expression_template(self) -> str:
        """Jinja template for selecting all fields (wildcard).

        Jinja variables:
            None

        Examples:
            Snowflake/PostgreSQL/BigQuery: "*"

        Tier: core
        Enables: wildcard SELECT
        """
        pass

    def escape_field_name_template(self) -> str:
        """Jinja template for escaping a field/column identifier.

        Jinja variables:
            field_name (str): The field name to escape.

        Examples:
            Snowflake: '"{{ field_name }}"'
            BigQuery: "`{{ field_name }}`"
            PostgreSQL: '"{{ field_name }}"'

        Tier: core
        Enables: safe column references
        """
        pass

    def get_table_identifier_template(self) -> str:
        """Jinja template for a fully-qualified table identifier.

        Jinja variables:
            database (str): Database name.
            schema (str): Schema name.
            table (str): Table name.

        Examples:
            Snowflake: "{{ database }}.{{ schema }}.{{ table }}"
            BigQuery: "`{{ database }}.{{ schema }}.{{ table }}`"

        Tier: core
        Enables: table references in queries
        """
        pass

    def get_arbitrary_where_clause_template(self) -> str:
        """Jinja template for an always-true WHERE clause.

        Jinja variables:
            None

        Examples:
            Snowflake/PostgreSQL: "TRUE"
            MySQL: "1=1"

        Tier: core
        Enables: default filter when no conditions specified
        """
        pass

    def ascending_order_template(self) -> str:
        """Jinja template for ascending ORDER BY direction.

        Jinja variables:
            field (str): Column or expression to order by.

        Examples:
            Snowflake/PostgreSQL: "{{ field }} ASC"

        Tier: core
        Enables: query result ordering
        """
        pass

    def descending_order_template(self) -> str:
        """Jinja template for descending ORDER BY direction.

        Jinja variables:
            field (str): Column or expression to order by.

        Examples:
            Snowflake/PostgreSQL: "{{ field }} DESC"

        Tier: core
        Enables: query result ordering
        """
        pass

    def get_case_when_func_template(self) -> str:
        """Jinja template for a CASE WHEN expression.

        Jinja variables:
            condition (str): Boolean expression for the WHEN clause.
            true_value (str): Value when condition is true.
            false_value (str): Value when condition is false.

        Examples:
            Snowflake/PostgreSQL: "CASE WHEN {{ condition }} THEN {{ true_value }} ELSE {{ false_value }} END"

        Tier: core
        Enables: conditional logic in queries
        """
        pass

    def negate_expression_template(self) -> str:
        """Jinja template for negating a boolean expression.

        Jinja variables:
            expression (str): The boolean expression to negate.

        Examples:
            Snowflake/PostgreSQL: "NOT({{ expression }})"

        Tier: core
        Enables: boolean logic in filters
        """
        pass

    ###################################################
    # QueryLanguage: String and Literal Handling
    ###################################################
    def escape_string_template(self) -> str:
        """Jinja template for escaping special characters in a string value.

        Jinja variables:
            value (str): The string value to escape.

        Examples:
            Snowflake/PostgreSQL: "{{ value | replace(\"'\", \"''\") }}"

        Tier: core
        Enables: safe string literal construction
        """
        pass

    def string_literal_template(self) -> str:
        """Jinja template for wrapping a value as a SQL string literal.

        Jinja variables:
            value (str): The already-escaped string value.

        Examples:
            Snowflake/PostgreSQL: "'{{ value }}'"

        Tier: core
        Enables: string literal values in queries
        """
        pass

    def literal_value_template(self) -> str:
        """Jinja template for a typed SQL literal value.

        Jinja variables:
            value (str): The literal value expression.

        Examples:
            Snowflake/PostgreSQL: "{{ value }}"

        Tier: core
        Enables: typed literal values in queries
        """
        pass

    def literal_datetime_template(self) -> str:
        """Jinja template for a SQL datetime literal.

        Jinja variables:
            value (datetime): Python datetime to render as SQL literal.

        Examples:
            Snowflake: "TIMESTAMP '{{ value.strftime('%Y-%m-%d %H:%M:%S') }}'"
            PostgreSQL: "TIMESTAMP '{{ value.strftime('%Y-%m-%d %H:%M:%S') }}'"

        Tier: core
        Enables: datetime literal values
        """
        pass

    def literal_time_of_day_template(self) -> str:
        """Jinja template for a SQL time-of-day literal.

        Jinja variables:
            value (str): Time-of-day string (e.g. "14:30:00").

        Examples:
            Snowflake/PostgreSQL: "TIME '{{ value }}'"

        Tier: standard
        Enables: intraday filter predicates
        """
        pass

    def literal_regex_template(self) -> str:
        """Jinja template for a SQL regex literal.

        Jinja variables:
            value (str): The regex pattern string.

        Examples:
            Snowflake/PostgreSQL: "'{{ value }}'"

        Tier: standard
        Enables: regex pattern literals in filter predicates
        """
        pass

    def literal_table_from_value_list_template(self) -> str:
        """Jinja template for creating an inline table from a list of values.

        Jinja variables:
            values (list[str]): SQL literal values to form rows.

        Examples:
            Snowflake: "SELECT column1 AS value FROM VALUES {{ values | join(', ') }}"

        Tier: standard
        Enables: IN/NOT IN list predicates
        """
        pass

    def date_literal_template(self) -> str:
        """Jinja template for a SQL DATE literal.

        Jinja variables:
            value (date): Python date to render as SQL literal.

        Examples:
            Snowflake: "DATE '{{ value.strftime('%Y-%m-%d') }}'"
            PostgreSQL: "DATE '{{ value.strftime('%Y-%m-%d') }}'"

        Tier: standard
        Enables: date literal values
        """
        pass

    def utc_literal_template(self) -> str:
        """Jinja template for a UTC timestamp literal.

        Jinja variables:
            value (datetime): Python datetime to render as UTC SQL literal.

        Examples:
            Snowflake: "TIMESTAMP '{{ value.strftime('%Y-%m-%d %H:%M:%S') }}' ::TIMESTAMP_TZ"
            PostgreSQL: "TIMESTAMP WITH TIME ZONE '{{ value.strftime('%Y-%m-%d %H:%M:%S') }}+00'"

        Tier: standard
        Enables: UTC timestamp literal values
        """
        pass

    ###################################################
    # QueryLanguage: Type Casting
    ###################################################
    def get_casting_to_numeric_expression_template(self) -> str:
        """Jinja template for casting a field to a numeric type.

        Jinja variables:
            field (str): Column name or expression to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS NUMERIC)"
            PostgreSQL: "CAST({{ field }} AS NUMERIC)"
            BigQuery: "CAST({{ field }} AS NUMERIC)"

        Tier: core
        Enables: rate denominator for all *_rate metrics
        """
        pass

    def cast_to_string_func_template(self) -> str:
        """Jinja template for casting a field to string/varchar.

        Jinja variables:
            field (str): Column name or expression to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS VARCHAR)"
            PostgreSQL: "CAST({{ field }} AS TEXT)"
            BigQuery: "CAST({{ field }} AS STRING)"

        Tier: core
        Enables: string conversions for timestamp and JSON operations
        """
        pass

    def get_casting_to_decimal_expression_template(self) -> str:
        """Jinja template for casting a field to decimal with precision.

        Jinja variables:
            field (str): Column name or expression to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS DECIMAL(38, 10))"
            PostgreSQL: "CAST({{ field }} AS DECIMAL(38, 10))"

        Tier: standard
        Enables: sum metric
        """
        pass

    def default_cast_to_timestamp_func_template(self) -> str:
        """Jinja template for casting a value to timestamp (default/fallback).

        Jinja variables:
            field (str): Value or column to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS TIMESTAMP)"
            PostgreSQL: "CAST({{ field }} AS TIMESTAMP)"

        Tier: core
        Enables: time range filters when field type is unknown
        """
        pass

    def cast_string_to_timestamp_template(self) -> str:
        """Jinja template for casting a string value to timestamp.

        Jinja variables:
            field (str): String expression to cast.

        Examples:
            Snowflake: "TRY_CAST({{ field }} AS TIMESTAMP)"
            PostgreSQL: "{{ field }}::TIMESTAMP"

        Tier: standard
        Enables: timestamp casting for string-typed time fields
        """
        pass

    def cast_numeric_to_timestamp_template(self) -> str:
        """Jinja template for casting a numeric (epoch) value to timestamp.

        Jinja variables:
            field (str): Numeric expression to cast.

        Examples:
            Snowflake: "TO_TIMESTAMP({{ field }})"
            PostgreSQL: "TO_TIMESTAMP({{ field }})"

        Tier: standard
        Enables: timestamp casting for epoch-typed time fields
        """
        pass

    def cast_date_to_timestamp_template(self) -> str:
        """Jinja template for casting a date value to timestamp.

        Jinja variables:
            field (str): Date expression to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS TIMESTAMP)"
            PostgreSQL: "{{ field }}::TIMESTAMP"

        Tier: standard
        Enables: timestamp casting for date-typed time fields
        """
        pass

    def cast_default_to_timestamp_template(self) -> str:
        """Jinja template for default timestamp casting when type is unknown.

        Jinja variables:
            field (str): Expression to cast.

        Examples:
            Snowflake: "TRY_CAST({{ field }} AS TIMESTAMP)"
            PostgreSQL: "CAST({{ field }} AS TIMESTAMP)"

        Tier: standard
        Enables: fallback timestamp casting
        """
        pass

    def cast_timestamp_to_date_template(self) -> str:
        """Jinja template for casting a timestamp to date type.

        Jinja variables:
            field (str): Timestamp expression to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS DATE)"
            PostgreSQL: "{{ field }}::DATE"

        Tier: standard
        Enables: timestamp-to-date conversion for filter predicates
        """
        pass

    def cast_timestamp_to_timestamp_ntz_template(self) -> str:
        """Jinja template for casting a timestamp to timestamp without timezone.

        Jinja variables:
            field (str): Timestamp expression to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS TIMESTAMP_NTZ)"
            PostgreSQL: "{{ field }}::TIMESTAMP WITHOUT TIME ZONE"

        Tier: standard
        Enables: timezone-naive timestamp comparisons
        """
        pass

    def cast_timestamp_to_timestamp_tz_template(self) -> str:
        """Jinja template for casting a timestamp to timestamp with timezone.

        Jinja variables:
            field (str): Timestamp expression to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS TIMESTAMP_TZ)"
            PostgreSQL: "{{ field }}::TIMESTAMP WITH TIME ZONE"

        Tier: standard
        Enables: timezone-aware timestamp comparisons
        """
        pass

    def cast_to_timestamp_with_tz_template(self) -> str:
        """Jinja template rendering the timestamp-with-timezone type name.

        Jinja variables:
            None

        Examples:
            Snowflake: "TIMESTAMPTZ"
            PostgreSQL: "TIMESTAMP WITH TIME ZONE"
            BigQuery: "TIMESTAMP"

        Tier: standard
        Enables: timezone-aware timestamp casting
        """
        pass

    def cast_to_timestamp_without_tz_template(self) -> str:
        """Jinja template rendering the timestamp-without-timezone type name.

        Jinja variables:
            None

        Examples:
            Snowflake: "TIMESTAMP_NTZ"
            PostgreSQL: "TIMESTAMP WITHOUT TIME ZONE"

        Tier: standard
        Enables: timezone-naive timestamp casting
        """
        pass

    ###################################################
    # QueryLanguage: Date/Time Functions
    ###################################################
    def convert_to_utc_template(self) -> str:
        """Jinja template for converting a timezone-aware field to UTC.

        Jinja variables:
            field (str): Timestamp expression with timezone.

        Examples:
            Snowflake: "CONVERT_TIMEZONE('UTC', {{ field }})"
            PostgreSQL: "{{ field }} AT TIME ZONE 'UTC'"

        Tier: standard
        Enables: UTC normalization for time range filters
        """
        pass

    def current_date_func_template(self) -> str:
        """Jinja template for the current date expression.

        Jinja variables:
            None

        Examples:
            Snowflake/PostgreSQL: "CURRENT_DATE"
            BigQuery: "CURRENT_DATE()"

        Tier: core
        Enables: date-based time range filters
        """
        pass

    def current_timestamp_func_template(self) -> str:
        """Jinja template for the current timestamp expression.

        Jinja variables:
            None

        Examples:
            Snowflake: "CURRENT_TIMESTAMP()"
            PostgreSQL: "NOW()"
            BigQuery: "CURRENT_TIMESTAMP()"

        Tier: core
        Enables: time range filters across all monitor types
        """
        pass

    def add_days_func_template(self) -> str:
        """Jinja template for adding/subtracting days from a date.

        Jinja variables:
            field (str): Date expression.
            days (int): Number of days to add (negative to subtract).

        Examples:
            Snowflake: "DATEADD(day, {{ days }}, {{ field }})"
            PostgreSQL: "{{ field }} + INTERVAL '{{ days }} days'"

        Tier: standard
        Enables: date arithmetic in time range filters
        """
        pass

    def add_days_timestamp_func_template(self) -> str:
        """Jinja template for adding/subtracting days from a timestamp.

        Jinja variables:
            field (str): Timestamp expression.
            days (int): Number of days to add (negative to subtract).

        Examples:
            Snowflake: "DATEADD(day, {{ days }}, {{ field }})"
            PostgreSQL: "{{ field }} + INTERVAL '{{ days }} days'"

        Tier: standard
        Enables: timestamp arithmetic in time range filters
        """
        pass

    def add_hours_timestamp_func_template(self) -> str:
        """Jinja template for adding/subtracting hours from a timestamp.

        Jinja variables:
            field (str): Timestamp expression.
            hours (int): Number of hours to add (negative to subtract).

        Examples:
            Snowflake: "DATEADD(hour, {{ hours }}, {{ field }})"
            PostgreSQL: "{{ field }} + INTERVAL '{{ hours }} hours'"

        Tier: standard
        Enables: hourly timestamp arithmetic
        """
        pass

    def time_truncate_func_template(self) -> str:
        """Jinja template for truncating a timestamp to a given interval.

        Jinja variables:
            field (str): Timestamp expression to truncate.
            truncation (str): Truncation interval (e.g. 'DAY', 'HOUR', 'MONTH').

        Examples:
            Snowflake: "DATE_TRUNC('{{ truncation }}', {{ field }})"
            PostgreSQL: "DATE_TRUNC('{{ truncation }}', {{ field }})"
            BigQuery: "TIMESTAMP_TRUNC({{ field }}, {{ truncation }})"

        Tier: standard
        Enables: time-bucketed aggregations
        """
        pass

    def truncate_to_day_template(self) -> str:
        """Jinja template for truncating a timestamp to day.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake: "DATE_TRUNC('DAY', {{ field }})"
            PostgreSQL: "DATE_TRUNC('day', {{ field }})"

        Tier: standard
        Enables: daily time bucketing
        """
        pass

    def truncate_to_hour_template(self) -> str:
        """Jinja template for truncating a timestamp to hour.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake: "DATE_TRUNC('HOUR', {{ field }})"
            PostgreSQL: "DATE_TRUNC('hour', {{ field }})"

        Tier: standard
        Enables: hourly time bucketing
        """
        pass

    def truncate_to_week_template(self) -> str:
        """Jinja template for truncating a timestamp to week.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake: "DATE_TRUNC('WEEK', {{ field }})"
            PostgreSQL: "DATE_TRUNC('week', {{ field }})"

        Tier: standard
        Enables: weekly time bucketing
        """
        pass

    def truncate_to_month_template(self) -> str:
        """Jinja template for truncating a timestamp to month.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake: "DATE_TRUNC('MONTH', {{ field }})"
            PostgreSQL: "DATE_TRUNC('month', {{ field }})"

        Tier: standard
        Enables: monthly time bucketing
        """
        pass

    def truncate_to_year_template(self) -> str:
        """Jinja template for truncating a timestamp to year.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake: "DATE_TRUNC('YEAR', {{ field }})"
            PostgreSQL: "DATE_TRUNC('year', {{ field }})"

        Tier: standard
        Enables: yearly time bucketing
        """
        pass

    def get_is_yesterday_expression_template(self) -> str:
        """Jinja template for checking if a timestamp falls on yesterday.

        Jinja variables:
            field (str): Timestamp expression to check.

        Examples:
            Snowflake: "CAST({{ field }} AS DATE) = DATEADD(day, -1, CURRENT_DATE)"
            PostgreSQL: "{{ field }}::DATE = CURRENT_DATE - INTERVAL '1 day'"

        Tier: standard
        Enables: yesterday filter in time range expressions
        """
        pass

    def get_in_past_days_expression_template(self) -> str:
        """Jinja template for checking if a timestamp is within the past N days.

        Jinja variables:
            field (str): Timestamp expression to check.
            days (int): Number of past days.

        Examples:
            Snowflake: "{{ field }} >= DATEADD(day, -{{ days }}, CURRENT_TIMESTAMP())"
            PostgreSQL: "{{ field }} >= NOW() - INTERVAL '{{ days }} days'"

        Tier: standard
        Enables: past-N-days time range filter
        """
        pass

    def get_in_past_hours_expression_template(self) -> str:
        """Jinja template for checking if a timestamp is within the past N hours.

        Jinja variables:
            field (str): Timestamp expression to check.
            hours (int): Number of past hours.

        Examples:
            Snowflake: "{{ field }} >= DATEADD(hour, -{{ hours }}, CURRENT_TIMESTAMP())"
            PostgreSQL: "{{ field }} >= NOW() - INTERVAL '{{ hours }} hours'"

        Tier: standard
        Enables: past-N-hours time range filter
        """
        pass

    def get_in_past_calendar_week_expression_template(self) -> str:
        """Jinja template for checking if a timestamp falls in the current calendar week.

        Jinja variables:
            field (str): Timestamp expression to check.

        Examples:
            Snowflake: "DATE_TRUNC('WEEK', {{ field }}) = DATE_TRUNC('WEEK', CURRENT_DATE)"
            PostgreSQL: "DATE_TRUNC('week', {{ field }}) = DATE_TRUNC('week', CURRENT_DATE)"

        Tier: standard
        Enables: calendar week filter
        """
        pass

    def get_in_past_calendar_month_expression_template(self) -> str:
        """Jinja template for checking if a timestamp falls in the current calendar month.

        Jinja variables:
            field (str): Timestamp expression to check.

        Examples:
            Snowflake: "DATE_TRUNC('MONTH', {{ field }}) = DATE_TRUNC('MONTH', CURRENT_DATE)"
            PostgreSQL: "DATE_TRUNC('month', {{ field }}) = DATE_TRUNC('month', CURRENT_DATE)"

        Tier: standard
        Enables: calendar month filter
        """
        pass

    def get_date_diff_func_template(self) -> str:
        """Jinja template for computing the difference between two dates/timestamps.

        Jinja variables:
            field1 (str): Start date/timestamp.
            field2 (str): End date/timestamp.
            unit (str): Unit of difference (e.g. 'day', 'hour').

        Examples:
            Snowflake: "DATEDIFF({{ unit }}, {{ field1 }}, {{ field2 }})"
            PostgreSQL: "EXTRACT(EPOCH FROM ({{ field2 }} - {{ field1 }})) / 86400"

        Tier: standard
        Enables: date/timestamp difference in comparison monitors
        """
        pass

    def get_days_of_week_expression_template(self) -> str:
        """Jinja template for extracting the day of week from a timestamp.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake: "DAYOFWEEK({{ field }})"
            PostgreSQL: "EXTRACT(DOW FROM {{ field }})"

        Tier: standard
        Enables: day-of-week filtering
        """
        pass

    def convert_to_unix_timestamp_func_template(self) -> str:
        """Jinja template for converting a field to Unix epoch seconds.

        Jinja variables:
            field (str): Timestamp expression to convert.

        Examples:
            Snowflake: "EXTRACT(EPOCH FROM {{ field }})"
            PostgreSQL: "EXTRACT(EPOCH FROM {{ field }})"

        Tier: standard
        Enables: Unix timestamp conversion for comparison monitors
        """
        pass

    ###################################################
    # QueryLanguage: Dialect Capability Flags
    ###################################################
    def supports_literal_select_template(self) -> str:
        """Jinja template rendering "true" or "false" for literal SELECT support.

        A database supports literal SELECT if `SELECT 1` works without a FROM clause.

        Jinja variables:
            None

        Examples:
            Snowflake/PostgreSQL: "true"
            Oracle: "false"

        Tier: core
        Enables: dialect flag for bare SELECT support
        """
        pass

    def supports_literal_group_by_template(self) -> str:
        """Jinja template rendering "true" or "false" for literal GROUP BY support.

        Jinja variables:
            None

        Examples:
            Snowflake/PostgreSQL: "true"

        Tier: core
        Enables: dialect flag for GROUP BY with literals
        """
        pass

    def supports_group_by_on_subquery_template(self) -> str:
        """Jinja template rendering "true" or "false" for GROUP BY on subquery support.

        Jinja variables:
            None

        Examples:
            Snowflake/PostgreSQL: "true"

        Tier: core
        Enables: dialect flag for ORDER BY inside subqueries
        """
        pass

    def parses_timestamp_with_trailing_text_template(self) -> str:
        """Jinja template rendering "true" or "false" for trailing text timestamp parsing.

        Some databases can parse "2024-01-01 extra text" as a timestamp.

        Jinja variables:
            None

        Examples:
            Snowflake: "true"
            PostgreSQL: "false"

        Tier: standard
        Enables: dialect flag for lenient timestamp parsing
        """
        pass

    ###################################################
    # QueryLanguage: Null and NaN Handling
    ###################################################
    def is_null_template(self) -> str:
        """Jinja template for IS NULL check.

        Jinja variables:
            field (str): Expression to check.

        Examples:
            Snowflake/PostgreSQL: "{{ field }} IS NULL"

        Tier: core
        Enables: null-check filter predicates
        """
        pass

    def is_not_null_template(self) -> str:
        """Jinja template for IS NOT NULL check.

        Jinja variables:
            field (str): Expression to check.

        Examples:
            Snowflake/PostgreSQL: "{{ field }} IS NOT NULL"

        Tier: core
        Enables: not-null filter predicates
        """
        pass

    def nan_expr_template(self) -> str:
        """Jinja template for a NaN literal expression.

        Jinja variables:
            None

        Examples:
            Snowflake: "'NaN'::FLOAT"
            PostgreSQL: "'NaN'::NUMERIC"
            BigQuery: "CAST('NaN' AS FLOAT64)"

        Tier: standard
        Enables: NaN detection in data quality metrics
        """
        pass

    def get_isnan_expression_template(self) -> str:
        """Jinja template for detecting NaN values.

        Jinja variables:
            field (str): Expression to check for NaN.

        Examples:
            Snowflake: "{{ field }} != {{ field }}"
            PostgreSQL: "{{ field }} = 'NaN'::NUMERIC"

        Tier: standard
        Enables: nan_count metric, nan_rate metric
        """
        pass

    ###################################################
    # QueryLanguage: Comparison Operators
    ###################################################
    def get_is_eq_expression_template(self) -> str:
        """Jinja template for equality comparison.

        Jinja variables:
            field1 (str): Left operand.
            field2 (str): Right operand.

        Examples:
            Snowflake/PostgreSQL: "{{ field1 }} = {{ field2 }}"

        Tier: standard
        Enables: threshold and custom rule evaluation in comparison monitors
        """
        pass

    def get_is_gt_expression_template(self) -> str:
        """Jinja template for greater-than comparison.

        Jinja variables:
            field1 (str): Left operand.
            field2 (str): Right operand.

        Examples:
            Snowflake/PostgreSQL: "{{ field1 }} > {{ field2 }}"

        Tier: standard
        Enables: threshold comparisons in comparison monitors
        """
        pass

    def get_is_gte_expression_template(self) -> str:
        """Jinja template for greater-than-or-equal comparison.

        Jinja variables:
            field1 (str): Left operand.
            field2 (str): Right operand.

        Examples:
            Snowflake/PostgreSQL: "{{ field1 }} >= {{ field2 }}"

        Tier: standard
        Enables: threshold comparisons in comparison monitors
        """
        pass

    def get_is_lt_expression_template(self) -> str:
        """Jinja template for less-than comparison.

        Jinja variables:
            field1 (str): Left operand.
            field2 (str): Right operand.

        Examples:
            Snowflake/PostgreSQL: "{{ field1 }} < {{ field2 }}"

        Tier: standard
        Enables: range checks in comparison monitors
        """
        pass

    def get_is_lte_expression_template(self) -> str:
        """Jinja template for less-than-or-equal comparison.

        Jinja variables:
            field1 (str): Left operand.
            field2 (str): Right operand.

        Examples:
            Snowflake/PostgreSQL: "{{ field1 }} <= {{ field2 }}"

        Tier: standard
        Enables: range checks in comparison monitors
        """
        pass

    def get_is_inside_range_expression_template(self) -> str:
        """Jinja template for checking if a value is inside a range (inclusive).

        Jinja variables:
            field (str): Expression to check.
            lower (str): Lower bound.
            upper (str): Upper bound.

        Examples:
            Snowflake/PostgreSQL: "{{ field }} >= {{ lower }} AND {{ field }} <= {{ upper }}"
            BigQuery: "{{ field }} BETWEEN {{ lower }} AND {{ upper }}"

        Tier: standard
        Enables: range-based custom rule evaluation
        """
        pass

    def get_is_outside_range_expression_template(self) -> str:
        """Jinja template for checking if a value is outside a range.

        Jinja variables:
            field (str): Expression to check.
            lower (str): Lower bound.
            upper (str): Upper bound.

        Examples:
            Snowflake/PostgreSQL: "{{ field }} < {{ lower }} OR {{ field }} > {{ upper }}"
            BigQuery: "NOT ({{ field }} BETWEEN {{ lower }} AND {{ upper }})"

        Tier: standard
        Enables: range-based custom rule evaluation
        """
        pass

    ###################################################
    # QueryLanguage: Aggregation Functions
    ###################################################
    def get_avg_function_template(self) -> str:
        """Jinja template for the SQL AVG() aggregate function.

        Jinja variables:
            field (str): Column name or expression to average.

        Examples:
            Snowflake/PostgreSQL/BigQuery: "AVG({{ field }})"

        Tier: standard
        Enables: numeric_mean metric
        """
        pass

    def get_stddev_function_template(self) -> str:
        """Jinja template for the SQL standard deviation function.

        Jinja variables:
            field (str): Column name or expression.

        Examples:
            Snowflake: "STDDEV({{ field }})"
            PostgreSQL: "STDDEV_SAMP({{ field }})"
            BigQuery: "STDDEV({{ field }})"

        Tier: standard
        Enables: numeric_stddev metric, text_std_length metric
        """
        pass

    def get_distinct_count_func_template(self) -> str:
        """Jinja template for COUNT(DISTINCT ...).

        Jinja variables:
            field (str): Column name or expression to count distinct values of.

        Examples:
            Snowflake/PostgreSQL: "COUNT(DISTINCT {{ field }})"

        Tier: standard
        Enables: approx_distinct_count metric, approx_distinctness metric
        """
        pass

    def get_distinct_func_template(self) -> str:
        """Jinja template for DISTINCT expression.

        Jinja variables:
            field (str): Column name or expression.

        Examples:
            Snowflake/PostgreSQL: "DISTINCT {{ field }}"

        Tier: standard
        Enables: distinctness queries
        """
        pass

    def get_safe_divide_template(self) -> str:
        """Jinja template for zero-safe division.

        Jinja variables:
            numerator (str): Numerator expression.
            denominator (str): Denominator expression.

        Examples:
            Snowflake: "DIV0({{ numerator }}, {{ denominator }})"
            PostgreSQL: "CASE WHEN {{ denominator }} = 0 THEN NULL ELSE {{ numerator }} / {{ denominator }} END"
            BigQuery: "SAFE_DIVIDE({{ numerator }}, {{ denominator }})"

        Tier: standard
        Enables: rate_count_if, capped_rate_sql calculations
        """
        pass

    def get_conditional_count_expression_template(self) -> str:
        """Jinja template for counting rows matching a condition.

        Jinja variables:
            condition (str): Boolean expression for counting.

        Examples:
            Snowflake: "COUNT_IF({{ condition }})"
            PostgreSQL: "COUNT(CASE WHEN {{ condition }} THEN 1 END)"

        Tier: standard
        Enables: zero_count, negative_count, nan_count, empty_string_count, true_count, false_count metrics
        """
        pass

    def get_approx_quantiles_func_template(self) -> str:
        """Jinja template for approximate quantile buckets.

        Jinja variables:
            field (str): Column name or expression.
            num_buckets (int): Number of quantile buckets.

        Examples:
            Snowflake: "APPROX_PERCENTILE({{ field }}, 0.5)"
            BigQuery: "APPROX_QUANTILES({{ field }}, {{ num_buckets }})"

        Tier: standard
        Enables: approx_quantiles metric
        """
        pass

    def get_approx_percentile_func_template(self) -> str:
        """Jinja template for approximate percentile calculation.

        Jinja variables:
            field (str): Column name or expression.
            percentile (float): Percentile value between 0 and 1.

        Examples:
            Snowflake: "APPROX_PERCENTILE({{ field }}, {{ percentile }})"
            PostgreSQL: "PERCENTILE_CONT({{ percentile }}) WITHIN GROUP (ORDER BY {{ field }})"

        Tier: standard
        Enables: numeric_median, percentile_20/40/60/80 metrics
        """
        pass

    def approx_distinct_func_template(self) -> str:
        """Jinja template for approximate distinct count.

        Jinja variables:
            field (str): Column name or expression.

        Examples:
            Snowflake: "APPROX_COUNT_DISTINCT({{ field }})"
            PostgreSQL: "COUNT(DISTINCT {{ field }})"
            BigQuery: "APPROX_COUNT_DISTINCT({{ field }})"

        Tier: standard
        Enables: approximate unique count
        """
        pass

    def any_value_template(self) -> str:
        """Jinja template for ANY_VALUE() aggregate.

        Jinja variables:
            field (str): Column name or expression.

        Examples:
            Snowflake: "ANY_VALUE({{ field }})"
            PostgreSQL: "MIN({{ field }})"
            BigQuery: "ANY_VALUE({{ field }})"

        Tier: standard
        Enables: comparison monitor GROUP BY queries
        """
        pass

    ###################################################
    # QueryLanguage: String Functions
    ###################################################
    def get_length_template(self) -> str:
        """Jinja template for string length.

        Jinja variables:
            field (str): String expression to measure.

        Examples:
            Snowflake: "LENGTH({{ field }})"
            PostgreSQL: "LENGTH({{ field }})"
            BigQuery: "LENGTH({{ field }})"

        Tier: standard
        Enables: text_mean_length, text_min_length, text_max_length, text_std_length metrics
        """
        pass

    def substring_func_template(self) -> str:
        """Jinja template for substring extraction.

        Jinja variables:
            field (str): String expression.
            start (int): Starting position (1-indexed).
            length (int): Number of characters to extract.

        Examples:
            Snowflake: "SUBSTR({{ field }}, {{ start }}, {{ length }})"
            PostgreSQL: "SUBSTRING({{ field }} FROM {{ start }} FOR {{ length }})"

        Tier: standard
        Enables: substring extraction
        """
        pass

    def get_is_empty_string_expression_template(self) -> str:
        """Jinja template for checking if a field is an empty string.

        Jinja variables:
            field (str): String expression to check.

        Examples:
            Snowflake/PostgreSQL: "{{ field }} = ''"

        Tier: standard
        Enables: empty_string_count metric, empty_string_rate metric
        """
        pass

    def get_regexp_expression_template(self) -> str:
        """Jinja template for regex matching expression.

        Jinja variables:
            field (str): String expression to match.
            pattern (str): Regex pattern.

        Examples:
            Snowflake: "REGEXP_LIKE({{ field }}, {{ pattern }})"
            PostgreSQL: "{{ field }} ~ {{ pattern }}"
            BigQuery: "REGEXP_CONTAINS({{ field }}, {{ pattern }})"

        Tier: standard
        Enables: regex filter predicates, sampling
        """
        pass

    def get_regexp_count_expression_template(self) -> str:
        """Jinja template for counting regex matches within a string.

        Jinja variables:
            field (str): String expression to search.
            pattern (str): Regex pattern to count matches of.

        Examples:
            Snowflake: "REGEXP_COUNT({{ field }}, {{ pattern }})"
            PostgreSQL: "(SELECT COUNT(*) FROM REGEXP_MATCHES({{ field }}, {{ pattern }}, 'g'))"

        Tier: standard
        Enables: text_int_count, text_number_count, text_uuid_count, text_email_address_count metrics
        """
        pass

    ###################################################
    # QueryLanguage: Array and Timestamp Validation
    ###################################################
    def array_expr_template(self) -> str:
        """Jinja template for constructing an array literal.

        Jinja variables:
            values (list): Values for the array.

        Examples:
            Snowflake: "ARRAY_CONSTRUCT({{ values | join(', ') }})"
            PostgreSQL: "ARRAY[{{ values | join(', ') }}]"
            BigQuery: "[{{ values | join(', ') }}]"

        Tier: advanced
        Enables: array literal construction
        """
        pass

    def get_array_length_func_template(self) -> str:
        """Jinja template for getting the length of an array.

        Jinja variables:
            field (str): Array expression.

        Examples:
            Snowflake: "ARRAY_SIZE({{ field }})"
            PostgreSQL: "ARRAY_LENGTH({{ field }}, 1)"
            BigQuery: "ARRAY_LENGTH({{ field }})"

        Tier: advanced
        Enables: array_null_rate metric
        """
        pass

    def get_is_timestamp_expression_template(self) -> str:
        """Jinja template for checking if a string is a valid timestamp.

        Jinja variables:
            field (str): String expression to validate.

        Examples:
            Snowflake: "TRY_CAST({{ field }} AS TIMESTAMP) IS NOT NULL"
            PostgreSQL: "{{ field }}::TIMESTAMP IS NOT NULL"

        Tier: advanced
        Enables: text_timestamp_count metric, text_timestamp_rate metric
        """
        pass

    def get_not_is_timestamp_expression_template(self) -> str:
        """Jinja template for checking if a string is NOT a valid timestamp.

        Jinja variables:
            field (str): String expression to validate.

        Examples:
            Snowflake: "TRY_CAST({{ field }} AS TIMESTAMP) IS NULL"
            PostgreSQL: "{{ field }}::TIMESTAMP IS NULL"

        Tier: advanced
        Enables: text_not_timestamp_count metric
        """
        pass

    def get_epoch_seconds_expression_template(self) -> str:
        """Jinja template for extracting epoch seconds from a timestamp.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake: "EXTRACT(EPOCH FROM {{ field }})"
            PostgreSQL: "EXTRACT(EPOCH FROM {{ field }})"

        Tier: advanced
        Enables: past_timestamp_count, future_timestamp_count, unix_zero_count metrics
        """
        pass

    def get_epoch_seconds_parameter_template(self) -> str:
        """Jinja template for epoch seconds parameter.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake/PostgreSQL: "EXTRACT(EPOCH FROM {{ field }})"

        Tier: advanced
        Enables: epoch seconds parameter extraction
        """
        pass

    ###################################################
    # QueryLanguage: Math Functions
    ###################################################
    def get_absolute_value_function_template(self) -> str:
        """Jinja template for absolute value.

        Jinja variables:
            field (str): Numeric expression.

        Examples:
            Snowflake/PostgreSQL/BigQuery: "ABS({{ field }})"

        Tier: standard
        Enables: metric sample summary calculations in RCA
        """
        pass

    def rand_func_template(self) -> str:
        """Jinja template for generating a random number.

        Jinja variables:
            None

        Examples:
            Snowflake: "RANDOM()"
            PostgreSQL: "RANDOM()"
            BigQuery: "RAND()"

        Tier: standard
        Enables: random sampling ORDER BY for RCA
        """
        pass

    ###################################################
    # QueryLanguage: RCA and Advanced Functions
    ###################################################
    def max_time_func_template(self) -> str:
        """Jinja template for MAX() over a temporal field.

        Jinja variables:
            field (str): Timestamp or date expression.

        Examples:
            Snowflake/PostgreSQL: "MAX({{ field }})"

        Tier: advanced
        Enables: freshness/time-based RCA queries
        """
        pass

    def unpivot_template(self) -> str:
        """Jinja template for unpivoting columns to rows.

        Jinja variables:
            query (str): Source query or table.
            columns (list[str]): Column names to unpivot.
            name_column (str): Name for the unpivoted column name field.
            value_column (str): Name for the unpivoted value field.

        Examples:
            Snowflake: "SELECT * FROM ({{ query }}) UNPIVOT ({{ value_column }} FOR {{ name_column }} IN ({{ columns | join(', ') }}))"

        Tier: advanced
        Enables: comparison monitor value transformations
        """
        pass

    ###################################################
    # QueryLanguage: Field Operations
    ###################################################
    def get_field_or_alias_template(self) -> str:
        """Jinja template for referencing a field or its alias.

        Jinja variables:
            field (str): Field name or alias.

        Examples:
            Snowflake/PostgreSQL: "{{ field }}"

        Tier: core
        Enables: field referencing in queries
        """
        pass
