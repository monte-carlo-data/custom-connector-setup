from typing import Any, List


class BaseConnector:
    credentials: dict[str, str]
    connection: Any
    cursor: Any

    ########################################
    # Connection Related Methods
    ########################################
    def create_connection(self) -> Any:
        """Create and return a database connection.

        Use self.credentials to access values from credentials.json's connect_args.

        Examples:
            PostgreSQL: psycopg2.connect(host=self.credentials["host"], ...)
            Snowflake: snowflake.connector.connect(account=self.credentials["account"], ...)
            BigQuery: google.cloud.bigquery.Client(project=self.credentials["project"])
        """
        pass

    def create_cursor(self) -> Any:
        """Create and return a cursor from the active connection.

        Called immediately after create_connection(). The returned cursor is
        used by execute_query() and fetch_all_results().

        Examples:
            Snowflake: self.connection.cursor()
            PostgreSQL: self.connection.cursor()
            BigQuery: (not applicable -- use the client directly)
        """
        pass

    def close_connection(self):
        """Clean up the cursor and connection when the test session ends.

        Examples:
            Snowflake: self.cursor.close(); self.connection.close()
            PostgreSQL: self.cursor.close(); self.connection.close()
            BigQuery: self.connection.close()
        """
        pass

    ########################################
    # Execution Related Methods
    ########################################
    def execute_query(self, query: str) -> None:
        """Execute a SQL query using the active cursor.

        Args:
            query (str): The rendered SQL query string to execute.

        Examples:
            Snowflake: self.cursor.execute(query)
            PostgreSQL: self.cursor.execute(query)
            BigQuery: self.cursor = self.connection.query(query)
        """
        pass

    def fetch_all_results(self) -> List[Any]:
        """Fetch and return all rows from the last executed query.

        Returns:
            List of tuples, one per result row.

        Examples:
            Snowflake: self.cursor.fetchall()
            PostgreSQL: self.cursor.fetchall()
            BigQuery: [row.values() for row in self.cursor.result()]
        """
        pass


class MetadataQueryTemplates:
    ########################################
    # Metadata Job Related Methods
    ########################################
    def get_databases_query_template(self) -> str:
        """Return a Jinja template string that produces a list of accessible databases.

        Jinja variables:
            None

        Examples:
            Snowflake: "SHOW DATABASES"
            PostgreSQL: "SELECT current_database()"
            BigQuery: "SELECT catalog_name FROM INFORMATION_SCHEMA.SCHEMATA GROUP BY 1"

        Enables: database discovery
        """
        pass

    def get_schemas_query_template(self) -> str:
        """Return a Jinja template string that produces schemas for a given database.

        Jinja variables:
            database_name (str): Name of the database to list schemas for.

        Examples:
            Snowflake: "SHOW SCHEMAS IN DATABASE {{ database_name }}"
            PostgreSQL: "SELECT schema_name FROM information_schema.schemata WHERE catalog_name = '{{ database_name }}'"
            BigQuery: "SELECT schema_name FROM `{{ database_name }}`.INFORMATION_SCHEMA.SCHEMATA"

        Enables: schema discovery
        """
        pass

    def get_tables_query_template(self) -> str:
        """Return a Jinja template string that produces tables and views for given schemas.

        Jinja variables:
            database_name (str): Name of the database.
            schemas (str): Comma-separated, quoted schema names.
            offset (int): Row offset for pagination.
            limit (int): Maximum rows to return.
            table_names (str, optional): Comma-separated, quoted table names to filter by.
                When provided, only tables matching these names are returned.
                Format matches schemas: "'table1', 'table2'"
                Use Jinja conditional: {% if table_names is defined and table_names %}AND table_name IN ({{ table_names }}){% endif %}

        Returns columns: database_name, schema_name, table_name, table_type,
            row_count (optional), byte_count (optional), last_update_time (optional),
            view_query (optional)

        Examples:
            Snowflake: "SELECT ... FROM {{ database_name }}.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA IN ({{ schemas }}) {% if table_names is defined and table_names %}AND TABLE_NAME IN ({{ table_names }}){% endif %} LIMIT {{ limit }} OFFSET {{ offset }}"
            PostgreSQL: "SELECT ... FROM information_schema.tables WHERE table_schema IN ({{ schemas }}) {% if table_names is defined and table_names %}AND table_name IN ({{ table_names }}){% endif %} LIMIT {{ limit }} OFFSET {{ offset }}"
            BigQuery: "SELECT ... FROM `{{ database_name }}`.INFORMATION_SCHEMA.TABLES WHERE table_schema IN ({{ schemas }}) {% if table_names is defined and table_names %}AND table_name IN ({{ table_names }}){% endif %} LIMIT {{ limit }} OFFSET {{ offset }}"

        Enables: table discovery, volume rows, volume bytes, freshness
        """
        pass

    def get_columns_query_template(self) -> str:
        """Return a Jinja template string that produces column metadata for given tables.

        Jinja variables:
            database_name (str): Name of the database.
            tables (str): Comma-separated, quoted full table identifiers.

        Returns columns: full_table_id, column_name, column_type

        Examples:
            Snowflake: "SELECT ... FROM {{ database_name }}.INFORMATION_SCHEMA.COLUMNS WHERE ..."
            PostgreSQL: "SELECT ... FROM information_schema.columns WHERE ..."
            BigQuery: "SELECT ... FROM `{{ database_name }}`.INFORMATION_SCHEMA.COLUMNS WHERE ..."

        Enables: schema collection
        """
        pass


class QueryLogCollectionTemplates:
    ########################################
    # Query Log Job Related Methods
    ########################################
    def get_query_logs_query_template(self) -> str:
        """Return a Jinja template string that produces query logs within a time range.

        Results are paginated using limit and offset to handle large volumes of logs.

        Jinja variables:
            start_time (datetime): Start of the time range (inclusive).
            end_time (datetime): End of the time range (exclusive).
            limit (int): Maximum number of rows to return per page.
            offset (int): Number of rows to skip for pagination.

        Expected output columns (in order):
            query_id (str): Unique identifier for the query. **Required.**
            start_time (datetime): When the query started executing. **Required.**
            end_time (datetime): When the query finished executing. **Required.**
            query_text (str): The SQL text of the query. **Required.**
            user (str): The user who executed the query. Optional.
            error_code (str): Error code if the query failed. Optional.
            error_text (str): Error message if the query failed. Optional.
            returned_rows (int): Number of rows returned by the query. Optional.

        Examples:
            Snowflake:
                "SELECT QUERY_ID, START_TIME, END_TIME, QUERY_TEXT,
                        USER_NAME, ERROR_CODE, ERROR_MESSAGE, ROWS_PRODUCED
                 FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
                 WHERE START_TIME >= '{{ start_time }}' AND START_TIME < '{{ end_time }}'
                 ORDER BY START_TIME
                 LIMIT {{ limit }} OFFSET {{ offset }}"

            PostgreSQL:
                "SELECT query_id, query_start, query_end, query,
                        usename, sqlstate, NULL, NULL
                 FROM pg_stat_activity
                 WHERE query_start >= '{{ start_time }}' AND query_start < '{{ end_time }}'
                 ORDER BY query_start
                 LIMIT {{ limit }} OFFSET {{ offset }}"

            BigQuery:
                "SELECT job_id, creation_time, end_time, query,
                        user_email, error_result.reason, error_result.message,
                        total_rows
                 FROM `region-us`.INFORMATION_SCHEMA.JOBS
                 WHERE creation_time >= '{{ start_time }}' AND creation_time < '{{ end_time }}'
                 ORDER BY creation_time
                 LIMIT {{ limit }} OFFSET {{ offset }}"

        Enables: query log collection, lineage, field lineage
        """
        pass


class CustomSQLMonitorTemplates:
    ###################################################
    # Custom SQL Monitors Related Methods
    ###################################################
    def transform_into_count_query_template(self) -> str:
        """Return a Jinja template string that wraps a query in a COUNT(*) outer query.

        Jinja variables:
            query (str): The inner SQL query to count rows from.

        Examples:
            Snowflake: "SELECT COUNT(*) FROM ({{ query }}) AS count_query"
            PostgreSQL: "SELECT COUNT(*) FROM ({{ query }}) AS count_query"
            BigQuery: "SELECT COUNT(*) FROM ({{ query }})"

        Enables: custom SQL monitor row counting
        """
        pass

    def add_row_limit_template(self) -> str:
        """Return a Jinja template string that adds a row limit to a query.

        Jinja variables:
            query (str): The SQL query to limit.
            limit (int): Maximum number of rows.

        Examples:
            Snowflake: "{{ query }} LIMIT {{ limit }}"
            PostgreSQL: "{{ query }} LIMIT {{ limit }}"
            BigQuery: "{{ query }} LIMIT {{ limit }}"

        Enables: custom SQL monitor row limiting
        """
        pass

    def get_count_all_expression_template(self) -> str:
        """Return a Jinja template string for a COUNT(*) expression.

        Jinja variables:
            None

        Examples:
            Snowflake: "COUNT(*)"
            PostgreSQL: "COUNT(*)"
            BigQuery: "COUNT(*)"

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
        """Return a Jinja template string for building a CTE (Common Table Expression).

        Jinja variables:
            alias (str): Name for the CTE.
            cte (str): The query body of the CTE.

        Examples:
            Snowflake: "WITH {{ alias }} AS ({{ cte }})"
            PostgreSQL: "WITH {{ alias }} AS ({{ cte }})"
            BigQuery: "WITH {{ alias }} AS ({{ cte }})"

        Enables: query assembly for all monitors
        """
        pass

    def add_select_clause_template(self) -> str:
        """Return a Jinja template string for a SELECT clause.

        Jinja variables:
            select_expressions (list[str]): List of field/expression strings.
                When empty, default to selecting all fields (e.g. "*").
            cte (str): Optional CTE prefix (e.g. "WITH alias AS (...)").
                When non-empty, prepend it before SELECT.

        Examples:
            Snowflake: "{% if cte %}{{ cte }} {% endif %}SELECT {{ select_expressions | join(', ') or '*' }}"
            PostgreSQL: "{% if cte %}{{ cte }} {% endif %}SELECT {{ select_expressions | join(', ') or '*' }}"
            BigQuery: "{% if cte %}{{ cte }} {% endif %}SELECT {{ select_expressions | join(', ') or '*' }}"

        Enables: query assembly for all monitors
        """
        pass

    def add_from_clause_template(self) -> str:
        """Return a Jinja template string for a FROM clause.

        Jinja variables:
            select_clause (str): The preceding SELECT clause to prepend.
            from_expression (str): Table name, identifier, or subquery to select from.

        Examples:
            Snowflake: "{{ select_clause }} FROM {{ from_expression }}"
            PostgreSQL: "{{ select_clause }} FROM {{ from_expression }}"
            BigQuery: "{{ select_clause }} FROM {{ from_expression }}"

        Enables: query assembly for all monitors
        """
        pass

    def union_queries_template(self) -> str:
        """Return a Jinja template string that combines multiple queries with UNION.

        Jinja variables:
            queries (list[str]): List of SQL queries to union.
            distinct (bool): If True, use UNION (deduplicates). If False, use UNION ALL.

        Examples:
            Snowflake: "{% if distinct %}{{ queries | join(' UNION ') }}{% else %}{{ queries | join(' UNION ALL ') }}{% endif %}"
            PostgreSQL: "{% if distinct %}{{ queries | join(' UNION ') }}{% else %}{{ queries | join(' UNION ALL ') }}{% endif %}"
            BigQuery: "{% if distinct %}{{ queries | join(' UNION DISTINCT ') }}{% else %}{{ queries | join(' UNION ALL ') }}{% endif %}"

        Enables: query assembly, CTE building
        """
        pass

    def alias_field_template(self) -> str:
        """Return a Jinja template string for aliasing a field expression.

        Jinja variables:
            field (str): The expression to alias.
            alias (str): The alias name.

        Examples:
            Snowflake: "{{ field }} AS {{ alias }}"
            PostgreSQL: "{{ field }} AS {{ alias }}"
            BigQuery: "{{ field }} AS {{ alias }}"

        Enables: query assembly for all monitors
        """
        pass

    def all_fields_expression_template(self) -> str:
        """Return a Jinja template string for selecting all fields (wildcard).

        Jinja variables:
            None

        Examples:
            Snowflake: "*"
            PostgreSQL: "*"
            BigQuery: "*"

        Enables: wildcard SELECT
        """
        pass

    def escape_field_name_template(self) -> str:
        """Return a Jinja template string for escaping a field/column identifier.

        Jinja variables:
            field_name (str): The field name to escape.

        Examples:
            Snowflake: '"{{ field_name }}"'
            PostgreSQL: '"{{ field_name }}"'
            BigQuery: "`{{ field_name }}`"

        Enables: safe column references
        """
        pass

    def get_table_identifier_template(self) -> str:
        """Return a Jinja template string for a fully-qualified table identifier.

        Jinja variables:
            database (str): Database name.
            schema (str): Schema name.
            table (str): Table name.

        Examples:
            Snowflake: "{{ database }}.{{ schema }}.{{ table }}"
            PostgreSQL: "{{ database }}.{{ schema }}.{{ table }}"
            BigQuery: "`{{ database }}.{{ schema }}.{{ table }}`"

        Enables: table references in queries
        """
        pass

    def get_arbitrary_where_clause_template(self) -> str:
        """Return a Jinja template string for an always-true WHERE clause.

        Jinja variables:
            None

        Examples:
            Snowflake: "TRUE"
            PostgreSQL: "TRUE"
            BigQuery: "TRUE"

        Enables: default filter when no conditions specified
        """
        pass

    def ascending_order_template(self) -> str:
        """Return a Jinja template string for ascending ORDER BY direction.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "{x} ASC"
            PostgreSQL: "{x} ASC"
            BigQuery: "{x} ASC"

        Enables: query result ordering
        """
        pass

    def descending_order_template(self) -> str:
        """Return a Jinja template string for descending ORDER BY direction.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "{x} DESC"
            PostgreSQL: "{x} DESC"
            BigQuery: "{x} DESC"

        Enables: query result ordering
        """
        pass

    def get_case_when_func_template(self) -> str:
        """Return a Jinja template string for a CASE WHEN expression.

        Jinja variables:
            conditions_and_results (list[tuple[str, str]]): List of (condition, result) pairs.
            else_result (str | None): Optional default value when no condition matches.

        Examples:
            Snowflake: "CASE {% for cond, res in conditions_and_results %}WHEN {{ cond }} THEN {{ res }} {% endfor %}{% if else_result %}ELSE {{ else_result }} {% endif %}END"
            PostgreSQL: "CASE {% for cond, res in conditions_and_results %}WHEN {{ cond }} THEN {{ res }} {% endfor %}{% if else_result %}ELSE {{ else_result }} {% endif %}END"
            BigQuery: "CASE {% for cond, res in conditions_and_results %}WHEN {{ cond }} THEN {{ res }} {% endfor %}{% if else_result %}ELSE {{ else_result }} {% endif %}END"

        Enables: conditional logic in queries
        """
        pass

    def negate_expression_template(self) -> str:
        """Return a Jinja template string for negating a boolean expression.

        Jinja variables:
            query (str): The boolean expression to negate.

        Examples:
            Snowflake: "NOT({{ query }})"
            PostgreSQL: "NOT({{ query }})"
            BigQuery: "NOT({{ query }})"

        Enables: boolean logic in filters
        """
        pass

    ###################################################
    # QueryLanguage: String and Literal Handling
    ###################################################
    def escape_string_template(self) -> str:
        """Return a Jinja template string for escaping special characters in a string value.

        Jinja variables:
            string (str): The string value to escape.

        Examples:
            Snowflake: "{{ string | replace(\"'\", \"''\") }}"
            PostgreSQL: "{{ string | replace(\"'\", \"''\") }}"
            BigQuery: "{{ string | replace(\"'\", \"''\") }}"

        Enables: safe string literal construction
        """
        pass

    def string_literal_template(self) -> str:
        """Return a Jinja template string for wrapping a value as a SQL string literal.

        Jinja variables:
            string (str): The already-escaped string value.

        Examples:
            Snowflake: "'{{ string }}'"
            PostgreSQL: "'{{ string }}'"
            BigQuery: "'{{ string }}'"

        Enables: string literal values in queries
        """
        pass

    def literal_value_template(self) -> str:
        """Return a Jinja template string for a typed SQL literal value.

        Jinja variables:
            value (str): The literal value expression.

        Examples:
            Snowflake: "{{ value }}"
            PostgreSQL: "{{ value }}"
            BigQuery: "{{ value }}"

        Enables: typed literal values in queries
        """
        pass

    def literal_datetime_template(self) -> str:
        """Return a Jinja template string for a SQL datetime literal.

        Jinja variables:
            date_time_value (datetime): Python datetime to render as SQL literal.

        Examples:
            Snowflake: "TIMESTAMP '{{ date_time_value.strftime('%Y-%m-%d %H:%M:%S') }}'"
            PostgreSQL: "TIMESTAMP '{{ date_time_value.strftime('%Y-%m-%d %H:%M:%S') }}'"
            BigQuery: "TIMESTAMP '{{ date_time_value.strftime('%Y-%m-%d %H:%M:%S') }}'"

        Enables: datetime literal values
        """
        pass

    def literal_time_of_day_template(self) -> str:
        """Return a Jinja template string for a SQL time-of-day literal.

        Jinja variables:
            value (str): Time-of-day string (e.g. "14:30:00").

        Examples:
            Snowflake: "TIME '{{ value }}'"
            PostgreSQL: "TIME '{{ value }}'"
            BigQuery: "TIME '{{ value }}'"

        Enables: intraday filter predicates
        """
        pass

    def literal_regex_template(self) -> str:
        """Return a Jinja template string for a SQL regex literal.

        Jinja variables:
            regex (str): The regex pattern string.

        Examples:
            Snowflake: "'{{ regex }}'"
            PostgreSQL: "'{{ regex }}'"
            BigQuery: "r'{{ regex }}'"

        Enables: regex pattern literals in filter predicates
        """
        pass

    def literal_table_from_value_list_template(self) -> str:
        """Return a Jinja template string for creating an inline table from a list of values.

        Jinja variables:
            field_type (str): Data type of the values (e.g. "NUMERIC", "TEXT").
            value_list (list[str]): SQL literal values to form rows.
            result_table_name (str): Alias for the resulting inline table.
            result_field_name (str): Alias for the value column.

        Examples:
            Snowflake: "SELECT column1 AS {{ result_field_name }} FROM VALUES {{ value_list | join(', ') }}"
            PostgreSQL: "SELECT unnest(ARRAY[{{ value_list | join(', ') }}]) AS {{ result_field_name }}"
            BigQuery: "SELECT {{ result_field_name }} FROM UNNEST([{{ value_list | join(', ') }}]) AS {{ result_field_name }}"

        Enables: IN/NOT IN list predicates
        """
        pass

    def date_literal_template(self) -> str:
        """Return a Jinja template string for a SQL DATE literal.

        Jinja variables:
            timestamp (date): Python date to render as SQL literal.

        Examples:
            Snowflake: "DATE '{{ timestamp.strftime('%Y-%m-%d') }}'"
            PostgreSQL: "DATE '{{ timestamp.strftime('%Y-%m-%d') }}'"
            BigQuery: "DATE '{{ timestamp.strftime('%Y-%m-%d') }}'"

        Enables: date literal values
        """
        pass

    def utc_literal_template(self) -> str:
        """Return a Jinja template string for a UTC timestamp literal.

        Jinja variables:
            timestamp (datetime): Python datetime to render as UTC SQL literal.
            field_type (str | None): Optional field type hint.

        Examples:
            Snowflake: "TIMESTAMP '{{ timestamp.strftime('%Y-%m-%d %H:%M:%S') }}' ::TIMESTAMP_TZ"
            PostgreSQL: "TIMESTAMP WITH TIME ZONE '{{ timestamp.strftime('%Y-%m-%d %H:%M:%S') }}+00'"
            BigQuery: "TIMESTAMP '{{ timestamp.strftime('%Y-%m-%d %H:%M:%S') }} UTC'"

        Enables: UTC timestamp literal values
        """
        pass

    ###################################################
    # QueryLanguage: Type Casting
    ###################################################
    def get_casting_to_numeric_expression_template(self) -> str:
        """Return a Jinja template string for casting a field to a numeric type.

        Jinja variables:
            expression (str): Column name or expression to cast.

        Examples:
            Snowflake: "CAST({{ expression }} AS NUMERIC)"
            PostgreSQL: "CAST({{ expression }} AS NUMERIC)"
            BigQuery: "CAST({{ expression }} AS NUMERIC)"

        Enables: rate denominator for all *_rate metrics
        """
        pass

    def cast_to_string_func_template(self) -> str:
        """Return a Jinja template string for casting a field to string/varchar.

        Jinja variables:
            expression (str): Column name or expression to cast.

        Examples:
            Snowflake: "CAST({{ expression }} AS VARCHAR)"
            PostgreSQL: "CAST({{ expression }} AS TEXT)"
            BigQuery: "CAST({{ expression }} AS STRING)"

        Enables: string conversions for timestamp and JSON operations
        """
        pass

    def get_casting_to_decimal_expression_template(self) -> str:
        """Return a Jinja template string for casting a field to decimal with precision.

        Jinja variables:
            expression (str): Column name or expression to cast.

        Examples:
            Snowflake: "CAST({{ expression }} AS DECIMAL(38, 10))"
            PostgreSQL: "CAST({{ expression }} AS DECIMAL(38, 10))"
            BigQuery: "CAST({{ expression }} AS BIGNUMERIC)"

        Enables: sum metric
        """
        pass

    def default_cast_to_timestamp_func_template(self) -> str:
        """Return a Jinja template string for casting a value to timestamp (default/fallback).

        Jinja variables:
            expression (str): Value or column to cast.

        Examples:
            Snowflake: "CAST({{ expression }} AS TIMESTAMP)"
            PostgreSQL: "CAST({{ expression }} AS TIMESTAMP)"
            BigQuery: "CAST({{ expression }} AS TIMESTAMP)"

        Enables: time range filters when field type is unknown
        """
        pass

    def cast_string_to_timestamp_template(self) -> str:
        """Return a Jinja template string for casting a string value to timestamp.

        Jinja variables:
            expression (str): String expression to cast.

        Examples:
            Snowflake: "TRY_CAST({{ expression }} AS TIMESTAMP)"
            PostgreSQL: "{{ expression }}::TIMESTAMP"
            BigQuery: "SAFE_CAST({{ expression }} AS TIMESTAMP)"

        Enables: timestamp casting for string-typed time fields
        """
        pass

    def cast_numeric_to_timestamp_template(self) -> str:
        """Return a Jinja template string for casting a numeric (epoch) value to timestamp.

        Jinja variables:
            expression (str): Numeric expression to cast.

        Examples:
            Snowflake: "TO_TIMESTAMP({{ expression }})"
            PostgreSQL: "TO_TIMESTAMP({{ expression }})"
            BigQuery: "TIMESTAMP_SECONDS(CAST({{ expression }} AS INT64))"

        Enables: timestamp casting for epoch-typed time fields
        """
        pass

    def cast_date_to_timestamp_template(self) -> str:
        """Return a Jinja template string for casting a date value to timestamp.

        Jinja variables:
            expression (str): Date expression to cast.

        Examples:
            Snowflake: "CAST({{ expression }} AS TIMESTAMP)"
            PostgreSQL: "{{ expression }}::TIMESTAMP"
            BigQuery: "CAST({{ expression }} AS TIMESTAMP)"

        Enables: timestamp casting for date-typed time fields
        """
        pass

    def cast_default_to_timestamp_template(self) -> str:
        """Return a Jinja template string for default timestamp casting when type is unknown.

        Jinja variables:
            expression (str): Expression to cast.

        Examples:
            Snowflake: "TRY_CAST({{ expression }} AS TIMESTAMP)"
            PostgreSQL: "CAST({{ expression }} AS TIMESTAMP)"
            BigQuery: "SAFE_CAST({{ expression }} AS TIMESTAMP)"

        Enables: fallback timestamp casting
        """
        pass

    def cast_timestamp_to_date_template(self) -> str:
        """Return a Jinja template string for casting a timestamp to date type.

        Jinja variables:
            timestamp (str): Timestamp expression to cast.

        Examples:
            Snowflake: "CAST({{ timestamp }} AS DATE)"
            PostgreSQL: "{{ timestamp }}::DATE"
            BigQuery: "CAST({{ timestamp }} AS DATE)"

        Enables: timestamp-to-date conversion for filter predicates
        """
        pass

    def cast_timestamp_to_timestamp_ntz_template(self) -> str:
        """Return a Jinja template string for casting a timestamp to timestamp without timezone.

        Jinja variables:
            timestamp (str): Timestamp expression to cast.

        Examples:
            Snowflake: "CAST({{ timestamp }} AS TIMESTAMP_NTZ)"
            PostgreSQL: "{{ timestamp }}::TIMESTAMP WITHOUT TIME ZONE"
            BigQuery: "{{ timestamp }}"

        Enables: timezone-naive timestamp comparisons
        """
        pass

    def cast_timestamp_to_timestamp_tz_template(self) -> str:
        """Return a Jinja template string for casting a timestamp to timestamp with timezone.

        Jinja variables:
            timestamp (str): Timestamp expression to cast.

        Examples:
            Snowflake: "CAST({{ timestamp }} AS TIMESTAMP_TZ)"
            PostgreSQL: "{{ timestamp }}::TIMESTAMP WITH TIME ZONE"
            BigQuery: "{{ timestamp }}"

        Enables: timezone-aware timestamp comparisons
        """
        pass

    def cast_to_timestamp_with_tz_template(self) -> str:
        """Return a Jinja template string for casting an expression to timestamp with timezone.

        Jinja variables:
            expression (str): The SQL expression to cast.

        Examples:
            Snowflake: "{{ expression }}::TIMESTAMPTZ"
            PostgreSQL: "{{ expression }}::TIMESTAMP WITH TIME ZONE"
            BigQuery: "CAST({{ expression }} AS TIMESTAMP)"

        Enables: timezone-aware timestamp casting
        """
        pass

    def cast_to_timestamp_without_tz_template(self) -> str:
        """Return a Jinja template string for casting an expression to timestamp without timezone.

        Jinja variables:
            expression (str): The SQL expression to cast.

        Examples:
            Snowflake: "{{ expression }}::TIMESTAMP_NTZ"
            PostgreSQL: "{{ expression }}::TIMESTAMP WITHOUT TIME ZONE"
            BigQuery: "CAST({{ expression }} AS TIMESTAMP)"

        Enables: timezone-naive timestamp casting
        """
        pass

    ###################################################
    # QueryLanguage: Date/Time Functions
    ###################################################
    def convert_to_utc_template(self) -> str:
        """Return a Jinja template string for converting a timestamp field to UTC.

        When ``timezone`` is provided and the column is tz-naive, the template
        should inline the tz-naive-to-UTC conversion (the same SQL that
        ``to_timezone_template`` would produce). When ``timezone`` is absent,
        the template handles tz-aware fields as before.

        Jinja variables:
            field (str): Timestamp expression.
            field_type (str | None): Column data type (optional).
            timezone (str | None): IANA timezone name or fixed UTC offset
                (e.g. "America/New_York", "+05:30") for tz-naive columns (optional).

        Examples:
            Snowflake: "{% if timezone is defined and timezone %}CONVERT_TIMEZONE('{{ timezone }}', 'UTC', {{ field }}){% else %}CONVERT_TIMEZONE('UTC', {{ field }}){% endif %}"
            PostgreSQL: "{% if timezone is defined and timezone %}TIMEZONE('UTC', TIMEZONE('{{ timezone }}', {{ field }})){% else %}{{ field }} AT TIME ZONE 'UTC'{% endif %}"
            BigQuery: "{% if timezone is defined and timezone %}TIMESTAMP({{ field }}, '{{ timezone }}'){% else %}TIMESTAMP({{ field }}, 'UTC'){% endif %}"

        Enables: UTC normalization for time range filters
        """
        pass

    def to_timezone_template(self) -> str:
        """Return a Jinja template string for converting a tz-naive field to UTC
        given a source timezone.

        Interprets ``field`` as being in ``timezone`` and returns the
        UTC-equivalent expression. The backend falls back to returning the
        field unchanged when this template is not implemented.

        Jinja variables:
            field (str): Tz-naive timestamp expression.
            timezone (str): IANA timezone name or fixed UTC offset
                (e.g. "America/New_York", "+05:30").

        Examples:
            Snowflake: "CONVERT_TIMEZONE('{{ timezone }}', 'UTC', {{ field }})"
            PostgreSQL: "TIMEZONE('UTC', TIMEZONE('{{ timezone }}', {{ field }}))"
            BigQuery: "TIMESTAMP({{ field }}, '{{ timezone }}')"
            Oracle: "SYS_EXTRACT_UTC(FROM_TZ(CAST({{ field }} AS TIMESTAMP), '{{ timezone }}'))"

        Enables: timezone offset support for tz-naive metric monitor time fields
        """
        pass

    def current_date_func_template(self) -> str:
        """Return a Jinja template string for the current date expression.

        Jinja variables:
            None

        Examples:
            Snowflake: "CURRENT_DATE"
            PostgreSQL: "CURRENT_DATE"
            BigQuery: "CURRENT_DATE()"

        Enables: date-based time range filters
        """
        pass

    def current_timestamp_func_template(self) -> str:
        """Return a Jinja template string for the current timestamp expression.

        Jinja variables:
            None

        Examples:
            Snowflake: "CURRENT_TIMESTAMP()"
            PostgreSQL: "NOW()"
            BigQuery: "CURRENT_TIMESTAMP()"

        Enables: time range filters across all monitor types
        """
        pass

    def add_days_func_template(self) -> str:
        """Return a Jinja template string for adding/subtracting days from a date.

        Jinja variables:
            date_expr (str): Date expression.
            days (int): Number of days to add (negative to subtract).

        Examples:
            Snowflake: "DATEADD(day, {{ days }}, {{ date_expr }})"
            PostgreSQL: "{{ date_expr }} + INTERVAL '{{ days }} days'"
            BigQuery: "DATE_ADD({{ date_expr }}, INTERVAL {{ days }} DAY)"

        Enables: date arithmetic in time range filters
        """
        pass

    def add_days_timestamp_func_template(self) -> str:
        """Return a Jinja template string for adding/subtracting days from a timestamp.

        Jinja variables:
            date_expr (str): Timestamp expression.
            days (int): Number of days to add (negative to subtract).

        Examples:
            Snowflake: "DATEADD(day, {{ days }}, {{ date_expr }})"
            PostgreSQL: "{{ date_expr }} + INTERVAL '{{ days }} days'"
            BigQuery: "TIMESTAMP_ADD({{ date_expr }}, INTERVAL {{ days }} DAY)"

        Enables: timestamp arithmetic in time range filters
        """
        pass

    def add_hours_timestamp_func_template(self) -> str:
        """Return a Jinja template string for adding/subtracting hours from a timestamp.

        Jinja variables:
            date_expr (str): Timestamp expression.
            hours (int): Number of hours to add (negative to subtract).

        Examples:
            Snowflake: "DATEADD(hour, {{ hours }}, {{ date_expr }})"
            PostgreSQL: "{{ date_expr }} + INTERVAL '{{ hours }} hours'"
            BigQuery: "TIMESTAMP_ADD({{ date_expr }}, INTERVAL {{ hours }} HOUR)"

        Enables: hourly timestamp arithmetic
        """
        pass

    def time_truncate_func_template(self) -> str:
        """Return a Jinja template string for truncating a timestamp to a given interval.

        Jinja variables:
            field (str): Timestamp expression to truncate.
            truncation (str): Truncation interval (e.g. 'DAY', 'HOUR', 'MONTH').

        Examples:
            Snowflake: "DATE_TRUNC('{{ truncation }}', {{ field }})"
            PostgreSQL: "DATE_TRUNC('{{ truncation }}', {{ field }})"
            BigQuery: "TIMESTAMP_TRUNC({{ field }}, {{ truncation }})"

        Enables: time-bucketed aggregations
        """
        pass

    def truncate_to_day_template(self) -> str:
        """Return a Jinja template string for truncating a timestamp to day.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake: "DATE_TRUNC('DAY', {{ field }})"
            PostgreSQL: "DATE_TRUNC('day', {{ field }})"
            BigQuery: "TIMESTAMP_TRUNC({{ field }}, DAY)"

        Enables: daily time bucketing
        """
        pass

    def truncate_to_hour_template(self) -> str:
        """Return a Jinja template string for truncating a timestamp to hour.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake: "DATE_TRUNC('HOUR', {{ field }})"
            PostgreSQL: "DATE_TRUNC('hour', {{ field }})"
            BigQuery: "TIMESTAMP_TRUNC({{ field }}, HOUR)"

        Enables: hourly time bucketing
        """
        pass

    def truncate_to_week_template(self) -> str:
        """Return a Jinja template string for truncating a timestamp to week.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake: "DATE_TRUNC('WEEK', {{ field }})"
            PostgreSQL: "DATE_TRUNC('week', {{ field }})"
            BigQuery: "TIMESTAMP_TRUNC({{ field }}, WEEK)"

        Enables: weekly time bucketing
        """
        pass

    def truncate_to_month_template(self) -> str:
        """Return a Jinja template string for truncating a timestamp to month.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake: "DATE_TRUNC('MONTH', {{ field }})"
            PostgreSQL: "DATE_TRUNC('month', {{ field }})"
            BigQuery: "TIMESTAMP_TRUNC({{ field }}, MONTH)"

        Enables: monthly time bucketing
        """
        pass

    def truncate_to_year_template(self) -> str:
        """Return a Jinja template string for truncating a timestamp to year.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake: "DATE_TRUNC('YEAR', {{ field }})"
            PostgreSQL: "DATE_TRUNC('year', {{ field }})"
            BigQuery: "TIMESTAMP_TRUNC({{ field }}, YEAR)"

        Enables: yearly time bucketing
        """
        pass

    def get_is_yesterday_expression_template(self) -> str:
        """Return a Jinja template string for checking if a timestamp falls on yesterday.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "CAST({x} AS DATE) = DATEADD(day, -1, CURRENT_DATE)"
            PostgreSQL: "{x}::DATE = CURRENT_DATE - INTERVAL '1 day'"
            BigQuery: "CAST({x} AS DATE) = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)"

        Enables: yesterday filter in time range expressions
        """
        pass

    def get_in_past_days_expression_template(self) -> str:
        """Return a Jinja template string for checking if a timestamp is within the past N days.

        Placeholder + Jinja variables:
            {x} (placeholder): Column or expression, substituted via .format(x=field_name).
            days (int): Number of past days.

        Examples:
            Snowflake: "{x} >= DATEADD(day, -{{ days }}, CURRENT_TIMESTAMP())"
            PostgreSQL: "{x} >= NOW() - INTERVAL '{{ days }} days'"
            BigQuery: "{x} >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {{ days }} DAY)"

        Enables: past-N-days time range filter
        """
        pass

    def get_in_past_hours_expression_template(self) -> str:
        """Return a Jinja template string for checking if a timestamp is within the past N hours.

        Placeholder + Jinja variables:
            {x} (placeholder): Column or expression, substituted via .format(x=field_name).
            hours (int): Number of past hours.

        Examples:
            Snowflake: "{x} >= DATEADD(hour, -{{ hours }}, CURRENT_TIMESTAMP())"
            PostgreSQL: "{x} >= NOW() - INTERVAL '{{ hours }} hours'"
            BigQuery: "{x} >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {{ hours }} HOUR)"

        Enables: past-N-hours time range filter
        """
        pass

    def get_in_past_calendar_week_expression_template(self) -> str:
        """Return a Jinja template string for checking if a timestamp falls in the current calendar week.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "DATE_TRUNC('WEEK', {x}) = DATE_TRUNC('WEEK', CURRENT_DATE)"
            PostgreSQL: "DATE_TRUNC('week', {x}) = DATE_TRUNC('week', CURRENT_DATE)"
            BigQuery: "TIMESTAMP_TRUNC({x}, WEEK) = TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), WEEK)"

        Enables: calendar week filter
        """
        pass

    def get_in_past_calendar_month_expression_template(self) -> str:
        """Return a Jinja template string for checking if a timestamp falls in the current calendar month.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "DATE_TRUNC('MONTH', {x}) = DATE_TRUNC('MONTH', CURRENT_DATE)"
            PostgreSQL: "DATE_TRUNC('month', {x}) = DATE_TRUNC('month', CURRENT_DATE)"
            BigQuery: "TIMESTAMP_TRUNC({x}, MONTH) = TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), MONTH)"

        Enables: calendar month filter
        """
        pass

    def get_date_diff_func_template(self) -> str:
        """Return a Jinja template string for computing the difference between two dates/timestamps.

        Jinja variables:
            date_expr1 (str): Start date/timestamp.
            date_expr2 (str): End date/timestamp.
            unit (str): Unit of difference (e.g. 'day', 'hour').

        Examples:
            Snowflake: "DATEDIFF({{ unit }}, {{ date_expr1 }}, {{ date_expr2 }})"
            PostgreSQL: "EXTRACT(EPOCH FROM ({{ date_expr2 }} - {{ date_expr1 }})) / 86400"
            BigQuery: "DATE_DIFF({{ date_expr2 }}, {{ date_expr1 }}, DAY)"

        Enables: date/timestamp difference in comparison monitors
        """
        pass

    def get_days_of_week_expression_template(self) -> str:
        """Return a Jinja template string for extracting the day of week from a timestamp.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "DAYOFWEEK({x})"
            PostgreSQL: "EXTRACT(DOW FROM {x})"
            BigQuery: "EXTRACT(DAYOFWEEK FROM {x})"

        Enables: day-of-week filtering
        """
        pass

    def convert_to_unix_timestamp_func_template(self) -> str:
        """Return a Jinja template string for converting a field to Unix epoch seconds.

        Jinja variables:
            date_expr (str): Timestamp expression to convert.

        Examples:
            Snowflake: "EXTRACT(EPOCH FROM {{ date_expr }})"
            PostgreSQL: "EXTRACT(EPOCH FROM {{ date_expr }})"
            BigQuery: "UNIX_SECONDS({{ date_expr }})"

        Enables: Unix timestamp conversion for comparison monitors
        """
        pass

    ###################################################
    # QueryLanguage: Dialect Capability Flags
    ###################################################
    def supports_literal_select_template(self) -> str:
        """Return a Jinja template string rendering "true" or "false" for literal SELECT support.

        A database supports literal SELECT if `SELECT 1` works without a FROM clause.

        Jinja variables:
            None

        Examples:
            Snowflake: "true"
            PostgreSQL: "true"
            BigQuery: "true"

        Enables: dialect flag for bare SELECT support
        """
        pass

    def supports_literal_group_by_template(self) -> str:
        """Return "true" or "false": can GROUP BY contain constant/literal expressions?

        When "true", the query builder may emit GROUP BY 'some_literal', 1, col_name.
        When "false", the query builder omits constants from GROUP BY and only
        groups by actual column references.

        T-SQL (SQL Server, Fabric) requires at least one non-constant column in
        every GROUP BY — grouping by a literal alone fails with:
        "Each GROUP BY expression must contain at least one column that is not
        an outer reference."

        Jinja variables:
            None

        Examples:
            Snowflake: "true"
            PostgreSQL: "true"
            BigQuery: "true"
            SQL Server / Fabric: "false"

        Enables: dialect flag for GROUP BY with literals
        """
        pass

    def supports_group_by_on_subquery_template(self) -> str:
        """Return "true" or "false": can ORDER BY appear inside subqueries and CTEs?

        When "true", the query builder may emit ORDER BY inside a CTE or derived
        table. When "false", ORDER BY is only added to the outermost query.

        T-SQL forbids ORDER BY inside CTEs and subqueries unless paired with
        TOP or OFFSET/FETCH. Bare ORDER BY inside a WITH clause fails with:
        "The ORDER BY clause is invalid in views, inline functions, derived
        tables, subqueries, and common table expressions."

        Jinja variables:
            None

        Examples:
            Snowflake: "true"
            PostgreSQL: "true"
            BigQuery: "true"
            SQL Server / Fabric: "false"

        Enables: dialect flag for ORDER BY inside subqueries
        """
        pass

    def parses_timestamp_with_trailing_text_template(self) -> str:
        """Return a Jinja template string rendering "true" or "false" for trailing text timestamp parsing.

        Some databases can parse "2024-01-01 extra text" as a timestamp.

        Jinja variables:
            None

        Examples:
            Snowflake: "true"
            PostgreSQL: "false"
            BigQuery: "false"

        Enables: dialect flag for lenient timestamp parsing
        """
        pass

    def supports_as_keyword_for_table_alias_template(self) -> str:
        """Return "true" or "false" for whether the database supports AS for table/subquery aliases.

        Most databases allow `FROM my_table AS t` and `FROM (...) AS sq`.
        Oracle (all versions) does not support AS for table aliases.
        Oracle 11g additionally does not support AS for subquery aliases.

        When this is "false", the query builder will emit `FROM my_table t`
        and `FROM (...) sq` instead of using AS.

        Jinja variables:
            None

        Examples:
            PostgreSQL: "true"
            Snowflake: "true"
            Oracle: "false"

        Enables: dialect flag for AS keyword usage in aliases
        """
        pass

    def supports_limit_0_template(self) -> str:
        """Return "true" or "false" for whether the database supports LIMIT 0 (or equivalent).

        Used to determine if the database can run a query that returns zero rows
        efficiently (e.g., for schema discovery via `SELECT * FROM t LIMIT 0`).

        Jinja variables:
            None

        Examples:
            PostgreSQL: "true"
            Snowflake: "true"
            Oracle: "true"  (uses ROWNUM <= 0)

        Enables: dialect flag for zero-row query support
        """
        pass

    def requires_subquery_alias_template(self) -> str:
        """Return "true" or "false" for whether the database requires subqueries to have aliases.

        Most databases require `FROM (SELECT ...) AS sq` (or without AS).
        Some databases like Oracle allow `FROM (SELECT ...)` with no alias.

        Jinja variables:
            None

        Examples:
            PostgreSQL: "true"
            Snowflake: "true"
            MySQL: "true"
            Oracle: "false"

        Enables: dialect flag for subquery alias requirements
        """
        pass

    ###################################################
    # QueryLanguage: Null and NaN Handling
    ###################################################
    def is_null_template(self) -> str:
        """Return a Jinja template string for an IS NULL check.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "{x} IS NULL"
            PostgreSQL: "{x} IS NULL"
            BigQuery: "{x} IS NULL"

        Enables: null-check filter predicates
        """
        pass

    def is_not_null_template(self) -> str:
        """Return a Jinja template string for an IS NOT NULL check.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "{x} IS NOT NULL"
            PostgreSQL: "{x} IS NOT NULL"
            BigQuery: "{x} IS NOT NULL"

        Enables: not-null filter predicates
        """
        pass

    def nan_expr_template(self) -> str:
        """Return a Jinja template string for a NaN literal expression.

        Jinja variables:
            None

        Examples:
            Snowflake: "'NaN'::FLOAT"
            PostgreSQL: "'NaN'::NUMERIC"
            BigQuery: "CAST('NaN' AS FLOAT64)"

        Enables: NaN detection in data quality metrics
        """
        pass

    def get_isnan_expression_template(self) -> str:
        """Return a Jinja template string for detecting NaN values.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "{x} != {x}"
            PostgreSQL: "{x} = 'NaN'::NUMERIC"
            BigQuery: "IS_NAN({x})"

        Enables: nan_count metric, nan_rate metric
        """
        pass

    ###################################################
    # QueryLanguage: Comparison Operators
    ###################################################
    def get_is_eq_expression_template(self) -> str:
        """Return a Jinja template string for equality comparison.

        Placeholder output (no Jinja variables):
            The template must output Python format-string placeholders {x} and {y}.
            They will be substituted later via .format(x=left, y=right).

        Examples:
            Snowflake: "{x} = {y}"
            PostgreSQL: "{x} = {y}"
            BigQuery: "{x} = {y}"

        Enables: threshold and custom rule evaluation in comparison monitors
        """
        pass

    def get_is_gt_expression_template(self) -> str:
        """Return a Jinja template string for greater-than comparison.

        Placeholder output (no Jinja variables):
            The template must output Python format-string placeholders {x} and {y}.
            They will be substituted later via .format(x=left, y=right).

        Examples:
            Snowflake: "{x} > {y}"
            PostgreSQL: "{x} > {y}"
            BigQuery: "{x} > {y}"

        Enables: threshold comparisons in comparison monitors
        """
        pass

    def get_is_gte_expression_template(self) -> str:
        """Return a Jinja template string for greater-than-or-equal comparison.

        Placeholder output (no Jinja variables):
            The template must output Python format-string placeholders {x} and {y}.
            They will be substituted later via .format(x=left, y=right).

        Examples:
            Snowflake: "{x} >= {y}"
            PostgreSQL: "{x} >= {y}"
            BigQuery: "{x} >= {y}"

        Enables: threshold comparisons in comparison monitors
        """
        pass

    def get_is_lt_expression_template(self) -> str:
        """Return a Jinja template string for less-than comparison.

        Placeholder output (no Jinja variables):
            The template must output Python format-string placeholders {x} and {y}.
            They will be substituted later via .format(x=left, y=right).

        Examples:
            Snowflake: "{x} < {y}"
            PostgreSQL: "{x} < {y}"
            BigQuery: "{x} < {y}"

        Enables: range checks in comparison monitors
        """
        pass

    def get_is_lte_expression_template(self) -> str:
        """Return a Jinja template string for less-than-or-equal comparison.

        Placeholder output (no Jinja variables):
            The template must output Python format-string placeholders {x} and {y}.
            They will be substituted later via .format(x=left, y=right).

        Examples:
            Snowflake: "{x} <= {y}"
            PostgreSQL: "{x} <= {y}"
            BigQuery: "{x} <= {y}"

        Enables: range checks in comparison monitors
        """
        pass

    def get_is_inside_range_expression_template(self) -> str:
        """Return a Jinja template string for checking if a value is inside a range (inclusive).

        Placeholder output (no Jinja variables):
            The template must output Python format-string placeholders
            {x}, {lower_threshold}, and {upper_threshold}.
            They will be substituted later via
            .format(x=field, lower_threshold=lower, upper_threshold=upper).

        Examples:
            Snowflake: "{x} >= {lower_threshold} AND {x} <= {upper_threshold}"
            PostgreSQL: "{x} >= {lower_threshold} AND {x} <= {upper_threshold}"
            BigQuery: "{x} BETWEEN {lower_threshold} AND {upper_threshold}"

        Enables: range-based custom rule evaluation
        """
        pass

    def get_is_outside_range_expression_template(self) -> str:
        """Return a Jinja template string for checking if a value is outside a range.

        Placeholder output (no Jinja variables):
            The template must output Python format-string placeholders
            {x}, {lower_threshold}, and {upper_threshold}.
            They will be substituted later via
            .format(x=field, lower_threshold=lower, upper_threshold=upper).

        Examples:
            Snowflake: "{x} < {lower_threshold} OR {x} > {upper_threshold}"
            PostgreSQL: "{x} < {lower_threshold} OR {x} > {upper_threshold}"
            BigQuery: "NOT ({x} BETWEEN {lower_threshold} AND {upper_threshold})"

        Enables: range-based custom rule evaluation
        """
        pass

    ###################################################
    # QueryLanguage: Aggregation Functions
    ###################################################
    def get_avg_function_template(self) -> str:
        """Return a Jinja template string for the SQL AVG() aggregate function.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "AVG({x})"
            PostgreSQL: "AVG({x})"
            BigQuery: "AVG({x})"

        Enables: numeric_mean metric
        """
        pass

    def get_stddev_function_template(self) -> str:
        """Return a Jinja template string for the SQL standard deviation function.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "STDDEV({x})"
            PostgreSQL: "STDDEV_SAMP({x})"
            BigQuery: "STDDEV({x})"

        Enables: numeric_stddev metric, text_std_length metric
        """
        pass

    def get_distinct_count_func_template(self) -> str:
        """Return a Jinja template string for COUNT(DISTINCT ...).

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "COUNT(DISTINCT {x})"
            PostgreSQL: "COUNT(DISTINCT {x})"
            BigQuery: "COUNT(DISTINCT {x})"

        Enables: approx_distinct_count metric, approx_distinctness metric
        """
        pass

    def get_distinct_func_template(self) -> str:
        """Return a Jinja template string for a DISTINCT expression.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "DISTINCT {x}"
            PostgreSQL: "DISTINCT {x}"
            BigQuery: "DISTINCT {x}"

        Enables: distinctness queries
        """
        pass

    def get_safe_divide_template(self) -> str:
        """Return a Jinja template string for zero-safe division.

        Jinja variables:
            dividend (str): Numerator expression.
            divisor (str): Denominator expression.

        Examples:
            Snowflake: "DIV0({{ dividend }}, {{ divisor }})"
            PostgreSQL: "CASE WHEN {{ divisor }} = 0 THEN NULL ELSE {{ dividend }} / {{ divisor }} END"
            BigQuery: "SAFE_DIVIDE({{ dividend }}, {{ divisor }})"

        Enables: rate_count_if, capped_rate_sql calculations
        """
        pass

    def get_conditional_count_expression_template(self) -> str:
        """Return a Jinja template string for counting rows matching a condition.

        Jinja variables:
            expression (str): Boolean expression for counting.

        Examples:
            Snowflake: "COUNT_IF({{ expression }})"
            PostgreSQL: "COUNT(CASE WHEN {{ expression }} THEN 1 END)"
            BigQuery: "COUNTIF({{ expression }})"

        Enables: zero_count, negative_count, nan_count, empty_string_count, true_count, false_count metrics
        """
        pass

    def get_approx_quantiles_func_template(self) -> str:
        """Return a Jinja template string for approximate quantile buckets.

        Jinja variables:
            expression (str): Column name or expression.
            num_buckets (int): Number of quantile buckets.

        Examples:
            Snowflake: "APPROX_PERCENTILE({{ expression }}, 0.5)"
            PostgreSQL: "PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {{ expression }})"
            BigQuery: "APPROX_QUANTILES({{ expression }}, {{ num_buckets }})"

        Enables: approx_quantiles metric
        """
        pass

    def get_approx_percentile_func_template(self) -> str:
        """Return a Jinja template string for approximate percentile calculation.

        Jinja variables:
            expression (str): Column name or expression.
            percentile (float): Percentile value between 0 and 1.

        Examples:
            Snowflake: "APPROX_PERCENTILE({{ expression }}, {{ percentile }})"
            PostgreSQL: "PERCENTILE_CONT({{ percentile }}) WITHIN GROUP (ORDER BY {{ expression }})"
            BigQuery: "APPROX_QUANTILES({{ expression }}, 100)[OFFSET(CAST({{ percentile }} * 100 AS INT64))]"

        Enables: numeric_median, percentile_20/40/60/80 metrics
        """
        pass

    def approx_distinct_func_template(self) -> str:
        """Return a Jinja template string for approximate distinct count.

        Jinja variables:
            field_name (str): Column name or expression.

        Examples:
            Snowflake: "APPROX_COUNT_DISTINCT({{ field_name }})"
            PostgreSQL: "COUNT(DISTINCT {{ field_name }})"
            BigQuery: "APPROX_COUNT_DISTINCT({{ field_name }})"

        Enables: approximate unique count
        """
        pass

    def any_value_template(self) -> str:
        """Return a Jinja template string for an ANY_VALUE() aggregate.

        Jinja variables:
            col_name (str): Column name or expression.

        Examples:
            Snowflake: "ANY_VALUE({{ col_name }})"
            PostgreSQL: "MIN({{ col_name }})"
            BigQuery: "ANY_VALUE({{ col_name }})"

        Enables: comparison monitor GROUP BY queries
        """
        pass

    ###################################################
    # QueryLanguage: String Functions
    ###################################################
    def get_length_template(self) -> str:
        """Return a Jinja template string for string length.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "LENGTH({x})"
            PostgreSQL: "LENGTH({x})"
            BigQuery: "LENGTH({x})"

        Enables: text_mean_length, text_min_length, text_max_length, text_std_length metrics
        """
        pass

    def substring_func_template(self) -> str:
        """Return a Jinja template string for substring extraction.

        Jinja variables:
            field (str): String expression.
            start_pos (int): Starting position (1-indexed).
            length (int): Number of characters to extract.

        Examples:
            Snowflake: "SUBSTR({{ field }}, {{ start_pos }}, {{ length }})"
            PostgreSQL: "SUBSTRING({{ field }} FROM {{ start_pos }} FOR {{ length }})"
            BigQuery: "SUBSTR({{ field }}, {{ start_pos }}, {{ length }})"

        Enables: substring extraction
        """
        pass

    def get_is_empty_string_expression_template(self) -> str:
        """Return a Jinja template string for checking if a field is an empty string.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "{x} = ''"
            PostgreSQL: "{x} = ''"
            BigQuery: "{x} = ''"

        Enables: empty_string_count metric, empty_string_rate metric
        """
        pass

    def get_regexp_expression_template(self) -> str:
        """Return a Jinja template string for regex matching expression.

        The template MUST include string quoting around {{ regexp }} — the framework
        passes the raw regex pattern, not a pre-rendered literal.

        Placeholder + Jinja variables:
            {x} (placeholder): Column or expression, substituted via .format(x=field_name).
            regexp (str): Raw regex pattern (unquoted).
            case_insensitive (bool): Whether to use case-insensitive matching.

        Examples:
            Snowflake: "REGEXP_LIKE({x}, '{{ regexp }}')"
            PostgreSQL: "{% if case_insensitive %}{x} ~* '{{ regexp }}'{% else %}{x} ~ '{{ regexp }}'{% endif %}"
            BigQuery: "REGEXP_CONTAINS({x}, r'{{ regexp }}')"

        Enables: regex filter predicates, sampling
        """
        pass

    def get_regexp_count_expression_template(self) -> str:
        """Return a Jinja template string for counting regex matches within a string.

        The template MUST include string quoting around {{ regexp }} — the framework
        passes the raw regex pattern, not a pre-rendered literal.

        Placeholder + Jinja variables:
            {x} (placeholder): Column or expression, substituted via .format(x=field_name).
            regexp (str): Raw regex pattern (unquoted).
            case_insensitive (bool): Whether to use case-insensitive matching.

        Examples:
            Snowflake: "REGEXP_COUNT({x}, '{{ regexp }}')"
            PostgreSQL: "(SELECT COUNT(*) FROM REGEXP_MATCHES({x}, '{{ regexp }}', '{% if case_insensitive %}gi{% else %}g{% endif %}'))"
            BigQuery: "ARRAY_LENGTH(REGEXP_EXTRACT_ALL({x}, r'{{ regexp }}'))"

        Enables: text_int_count, text_number_count, text_uuid_count, text_email_address_count metrics
        """
        pass

    ###################################################
    # QueryLanguage: Array and Timestamp Validation
    ###################################################
    def array_expr_template(self) -> str:
        """Return a Jinja template string for constructing an array literal.

        Jinja variables:
            values (list): Values for the array.

        Examples:
            Snowflake: "ARRAY_CONSTRUCT({{ values | join(', ') }})"
            PostgreSQL: "ARRAY[{{ values | join(', ') }}]"
            BigQuery: "[{{ values | join(', ') }}]"

        Enables: array literal construction
        """
        pass

    def get_array_length_func_template(self) -> str:
        """Return a Jinja template string for getting the length of an array.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "ARRAY_SIZE({x})"
            PostgreSQL: "ARRAY_LENGTH({x}, 1)"
            BigQuery: "ARRAY_LENGTH({x})"

        Enables: array_null_rate metric
        """
        pass

    def get_is_timestamp_expression_template(self) -> str:
        """Return a Jinja template string for checking if a string is a valid timestamp.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "TRY_CAST({x} AS TIMESTAMP) IS NOT NULL"
            PostgreSQL: "{x} ~ '^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][T ][0-9][0-9]:[0-9][0-9]:[0-9][0-9]'"
            BigQuery: "SAFE_CAST({x} AS TIMESTAMP) IS NOT NULL"

        Enables: text_timestamp_count metric, text_timestamp_rate metric
        """
        pass

    def get_not_is_timestamp_expression_template(self) -> str:
        """Return a Jinja template string for checking if a string is NOT a valid timestamp.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "TRY_CAST({x} AS TIMESTAMP) IS NULL"
            PostgreSQL: "{x} !~ '^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][T ][0-9][0-9]:[0-9][0-9]:[0-9][0-9]'"
            BigQuery: "SAFE_CAST({x} AS TIMESTAMP) IS NULL"

        Enables: text_not_timestamp_count metric
        """
        pass

    def get_epoch_seconds_expression_template(self) -> str:
        """Return a Jinja template string for extracting epoch seconds from a timestamp.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "EXTRACT(EPOCH FROM {x})"
            PostgreSQL: "EXTRACT(EPOCH FROM {x})"
            BigQuery: "UNIX_SECONDS({x})"

        Enables: past_timestamp_count, future_timestamp_count, unix_zero_count metrics
        """
        pass

    def get_epoch_seconds_parameter_template(self) -> str:
        """Return a Jinja template string for epoch seconds parameter.

        Placeholder output (no Jinja variables):
            The template must output a Python format-string placeholder {x}.
            It will be substituted later via .format(x=field_name).

        Examples:
            Snowflake: "EXTRACT(EPOCH FROM {x})"
            PostgreSQL: "EXTRACT(EPOCH FROM {x})"
            BigQuery: "UNIX_SECONDS({x})"

        Enables: epoch seconds parameter extraction
        """
        pass

    ###################################################
    # QueryLanguage: Math Functions
    ###################################################
    def get_absolute_value_function_template(self) -> str:
        """Return a Jinja template string for absolute value.

        Jinja variables:
            expression (str): Numeric expression.

        Examples:
            Snowflake: "ABS({{ expression }})"
            PostgreSQL: "ABS({{ expression }})"
            BigQuery: "ABS({{ expression }})"

        Enables: metric sample summary calculations in RCA
        """
        pass

    def rand_func_template(self) -> str:
        """Return a Jinja template string for generating a random number.

        Jinja variables:
            None

        Examples:
            Snowflake: "RANDOM()"
            PostgreSQL: "RANDOM()"
            BigQuery: "RAND()"

        Enables: random sampling ORDER BY for RCA
        """
        pass

    ###################################################
    # QueryLanguage: RCA and Advanced Functions
    ###################################################
    def max_time_func_template(self) -> str:
        """Return a Jinja template string for MAX() over a temporal field.

        Jinja variables:
            field (str): Timestamp or date expression.

        Examples:
            Snowflake: "MAX({{ field }})"
            PostgreSQL: "MAX({{ field }})"
            BigQuery: "MAX({{ field }})"

        Enables: freshness/time-based RCA queries
        """
        pass

    def unpivot_template(self) -> str:
        """Return a Jinja template string for unpivoting columns to rows.

        Jinja variables:
            from_table (str): Source query or table expression.
            column_list (list[str]): Column names to unpivot.
            name_column (str): Name for the unpivoted column name field.
            value_column (str): Name for the unpivoted value field.

        Examples:
            Snowflake: "SELECT * FROM ({{ from_table }}) UNPIVOT ({{ value_column }} FOR {{ name_column }} IN ({{ column_list | join(', ') }}))"
            PostgreSQL: "SELECT {{ name_column }}, {{ value_column }} FROM ({{ from_table }}) src CROSS JOIN LATERAL (VALUES ...) AS unpivoted({{ name_column }}, {{ value_column }})"
            BigQuery: "SELECT * FROM ({{ from_table }}) UNPIVOT ({{ value_column }} FOR {{ name_column }} IN ({{ column_list | join(', ') }}))"

        Enables: comparison monitor value transformations
        """
        pass

    ###################################################
    # QueryLanguage: Field Operations
    ###################################################
    def get_field_or_alias_template(self) -> str:
        """Return a Jinja template string for referencing a field or its alias.

        Jinja variables:
            field (str): Field name or alias.

        Examples:
            Snowflake: "{{ field }}"
            PostgreSQL: "{{ field }}"
            BigQuery: "{{ field }}"

        Enables: field referencing in queries
        """
        pass


class FunctionalTestOperations:
    """Optional stubs for functional validation tests.

    Implement these methods to enable tests that verify metadata queries
    reflect real-time database changes (not stale statistics).

    Template methods return Jinja template strings, just like the other
    template classes. The test framework renders and executes them.

    Every template receives ``database``, ``schema``, and ``table`` as
    Jinja variables — these are derived from get_test_table_identifier()
    so the table identity is defined in exactly one place.
    """

    def get_test_table_identifier(self) -> tuple:
        """Return (database, schema, table_name) for the test table.

        This is the single source of truth for the test table identity.
        The returned values are injected as ``{{ database }}``,
        ``{{ schema }}``, and ``{{ table }}`` into every template.

        Examples:
            Snowflake: return ("MY_TEST_DB", "PUBLIC", "PANDORA_FUNCTIONAL_TEST")
            PostgreSQL: return ("monolith", "public", "pandora_functional_test")
            BigQuery: return ("my-project", "my_dataset", "pandora_functional_test")
        """
        raise NotImplementedError

    def create_test_table_template(self) -> str:
        """Return a Jinja template string that creates the test table.

        Jinja variables:
            database (str): Database name from get_test_table_identifier().
            schema (str): Schema name from get_test_table_identifier().
            table (str): Table name from get_test_table_identifier().

        Examples:
            Snowflake: "CREATE TABLE {{ database }}.{{ schema }}.{{ table }} (id INT AUTOINCREMENT, value VARCHAR)"
            PostgreSQL: "CREATE TABLE {{ schema }}.{{ table }} (id SERIAL PRIMARY KEY, value TEXT)"
            BigQuery: "CREATE TABLE `{{ database }}.{{ schema }}.{{ table }}` (id INT64, value STRING)"

        Enables: functional validation tests
        """
        raise NotImplementedError

    def insert_rows_template(self) -> str:
        """Return a Jinja template string that inserts rows into the test table.

        Jinja variables:
            database (str): Database name from get_test_table_identifier().
            schema (str): Schema name from get_test_table_identifier().
            table (str): Table name from get_test_table_identifier().
            num_rows (int): Number of rows to insert.

        Examples:
            Snowflake: "INSERT INTO {{ database }}.{{ schema }}.{{ table }} (value) SELECT 'row_' || SEQ4() FROM TABLE(GENERATOR(ROWCOUNT => {{ num_rows }}))"
            PostgreSQL: "INSERT INTO {{ schema }}.{{ table }} (value) SELECT 'row_' || g FROM generate_series(1, {{ num_rows }}) g"
            BigQuery: "INSERT INTO `{{ database }}.{{ schema }}.{{ table }}` (value) SELECT CONCAT('row_', CAST(n AS STRING)) FROM UNNEST(GENERATE_ARRAY(1, {{ num_rows }})) n"

        Enables: functional validation tests (volume, freshness)
        """
        raise NotImplementedError

    def add_column_template(self) -> str:
        """Return a Jinja template string that adds a column to the test table.

        Jinja variables:
            database (str): Database name from get_test_table_identifier().
            schema (str): Schema name from get_test_table_identifier().
            table (str): Table name from get_test_table_identifier().
            column_name (str): Name of the column to add.
            column_type (str): SQL data type for the new column.

        Examples:
            Snowflake: "ALTER TABLE {{ database }}.{{ schema }}.{{ table }} ADD COLUMN {{ column_name }} {{ column_type }}"
            PostgreSQL: "ALTER TABLE {{ schema }}.{{ table }} ADD COLUMN {{ column_name }} {{ column_type }}"
            BigQuery: "ALTER TABLE `{{ database }}.{{ schema }}.{{ table }}` ADD COLUMN {{ column_name }} {{ column_type }}"

        Enables: functional validation tests (schema change)
        """
        raise NotImplementedError

    def drop_column_template(self) -> str:
        """Return a Jinja template string that drops a column from the test table.

        Jinja variables:
            database (str): Database name from get_test_table_identifier().
            schema (str): Schema name from get_test_table_identifier().
            table (str): Table name from get_test_table_identifier().
            column_name (str): Name of the column to drop.

        Examples:
            Snowflake: "ALTER TABLE {{ database }}.{{ schema }}.{{ table }} DROP COLUMN {{ column_name }}"
            PostgreSQL: "ALTER TABLE {{ schema }}.{{ table }} DROP COLUMN {{ column_name }}"
            BigQuery: "ALTER TABLE `{{ database }}.{{ schema }}.{{ table }}` DROP COLUMN {{ column_name }}"

        Enables: functional validation tests (schema change)
        """
        raise NotImplementedError

    def drop_test_table_template(self) -> str:
        """Return a Jinja template string that drops the test table.

        Use IF EXISTS to avoid errors when the table does not exist.

        Jinja variables:
            database (str): Database name from get_test_table_identifier().
            schema (str): Schema name from get_test_table_identifier().
            table (str): Table name from get_test_table_identifier().

        Examples:
            Snowflake: "DROP TABLE IF EXISTS {{ database }}.{{ schema }}.{{ table }}"
            PostgreSQL: "DROP TABLE IF EXISTS {{ schema }}.{{ table }}"
            BigQuery: "DROP TABLE IF EXISTS `{{ database }}.{{ schema }}.{{ table }}`"

        Enables: functional validation tests (cleanup)
        """
        raise NotImplementedError

    def create_lineage_query_template(self) -> str:
        """Return a Jinja template string for a SELECT query that should appear in query logs.

        Jinja variables:
            database (str): Database name from get_test_table_identifier().
            schema (str): Schema name from get_test_table_identifier().
            table (str): Table name from get_test_table_identifier().

        Examples:
            Snowflake: "SELECT * FROM {{ database }}.{{ schema }}.{{ table }} WHERE 1=0"
            PostgreSQL: "SELECT * FROM {{ schema }}.{{ table }} WHERE 1=0"
            BigQuery: "SELECT * FROM `{{ database }}.{{ schema }}.{{ table }}` WHERE 1=0"

        Enables: functional validation tests (query log capture)
        """
        raise NotImplementedError
