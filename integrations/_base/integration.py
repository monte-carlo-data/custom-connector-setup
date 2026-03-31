from typing import Any, List


class BaseIntegration:
    credentials: dict[str, str]
    connection: Any
    cursor: Any

    ########################################
    # Connection Related Methods
    ########################################
    def credential_env_vars(self) -> dict[str, str]:
        """Map credential keys to environment variable names.

        Return a dict where each key is a logical credential name you'll use
        in create_connection() via self.credentials[key], and each value is the
        environment variable name defined in your .env file.

        Examples:
            PostgreSQL (.env has PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD):
                return {
                    "host": "PGHOST",
                    "port": "PGPORT",
                    "database": "PGDATABASE",
                    "user": "PGUSER",
                    "password": "PGPASSWORD",
                }

            Snowflake (.env has SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, ...):
                return {
                    "account": "SNOWFLAKE_ACCOUNT",
                    "user": "SNOWFLAKE_USER",
                    "password": "SNOWFLAKE_PASSWORD",
                    "warehouse": "SNOWFLAKE_WAREHOUSE",
                    "database": "SNOWFLAKE_DATABASE",
                }
        """
        return {}

    def create_connection(self) -> Any:
        """Create and return a database connection.

        Use self.credentials to access any values mapped by credential_env_vars().

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
            query (str): The query body of the CTE.

        Examples:
            Snowflake: "WITH {{ alias }} AS ({{ query }})"
            PostgreSQL: "WITH {{ alias }} AS ({{ query }})"
            BigQuery: "WITH {{ alias }} AS ({{ query }})"

        Enables: query assembly for all monitors
        """
        pass

    def add_select_clause_template(self) -> str:
        """Return a Jinja template string for a SELECT clause.

        Jinja variables:
            fields (str): Comma-separated list of fields/expressions.

        Examples:
            Snowflake: "SELECT {{ fields }}"
            PostgreSQL: "SELECT {{ fields }}"
            BigQuery: "SELECT {{ fields }}"

        Enables: query assembly for all monitors
        """
        pass

    def add_from_clause_template(self) -> str:
        """Return a Jinja template string for a FROM clause.

        Jinja variables:
            table (str): Table name or alias to select from.

        Examples:
            Snowflake: "FROM {{ table }}"
            PostgreSQL: "FROM {{ table }}"
            BigQuery: "FROM {{ table }}"

        Enables: query assembly for all monitors
        """
        pass

    def union_queries_template(self) -> str:
        """Return a Jinja template string that combines multiple queries with UNION ALL.

        Jinja variables:
            queries (list[str]): List of SQL queries to union.

        Examples:
            Snowflake: "{{ queries | join(' UNION ALL ') }}"
            PostgreSQL: "{{ queries | join(' UNION ALL ') }}"
            BigQuery: "{{ queries | join(' UNION ALL ') }}"

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

        Jinja variables:
            field (str): Column or expression to order by.

        Examples:
            Snowflake: "{{ field }} ASC"
            PostgreSQL: "{{ field }} ASC"
            BigQuery: "{{ field }} ASC"

        Enables: query result ordering
        """
        pass

    def descending_order_template(self) -> str:
        """Return a Jinja template string for descending ORDER BY direction.

        Jinja variables:
            field (str): Column or expression to order by.

        Examples:
            Snowflake: "{{ field }} DESC"
            PostgreSQL: "{{ field }} DESC"
            BigQuery: "{{ field }} DESC"

        Enables: query result ordering
        """
        pass

    def get_case_when_func_template(self) -> str:
        """Return a Jinja template string for a CASE WHEN expression.

        Jinja variables:
            condition (str): Boolean expression for the WHEN clause.
            true_value (str): Value when condition is true.
            false_value (str): Value when condition is false.

        Examples:
            Snowflake: "CASE WHEN {{ condition }} THEN {{ true_value }} ELSE {{ false_value }} END"
            PostgreSQL: "CASE WHEN {{ condition }} THEN {{ true_value }} ELSE {{ false_value }} END"
            BigQuery: "CASE WHEN {{ condition }} THEN {{ true_value }} ELSE {{ false_value }} END"

        Enables: conditional logic in queries
        """
        pass

    def negate_expression_template(self) -> str:
        """Return a Jinja template string for negating a boolean expression.

        Jinja variables:
            expression (str): The boolean expression to negate.

        Examples:
            Snowflake: "NOT({{ expression }})"
            PostgreSQL: "NOT({{ expression }})"
            BigQuery: "NOT({{ expression }})"

        Enables: boolean logic in filters
        """
        pass

    ###################################################
    # QueryLanguage: String and Literal Handling
    ###################################################
    def escape_string_template(self) -> str:
        """Return a Jinja template string for escaping special characters in a string value.

        Jinja variables:
            value (str): The string value to escape.

        Examples:
            Snowflake: "{{ value | replace(\"'\", \"''\") }}"
            PostgreSQL: "{{ value | replace(\"'\", \"''\") }}"
            BigQuery: "{{ value | replace(\"'\", \"''\") }}"

        Enables: safe string literal construction
        """
        pass

    def string_literal_template(self) -> str:
        """Return a Jinja template string for wrapping a value as a SQL string literal.

        Jinja variables:
            value (str): The already-escaped string value.

        Examples:
            Snowflake: "'{{ value }}'"
            PostgreSQL: "'{{ value }}'"
            BigQuery: "'{{ value }}'"

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
            value (datetime): Python datetime to render as SQL literal.

        Examples:
            Snowflake: "TIMESTAMP '{{ value.strftime('%Y-%m-%d %H:%M:%S') }}'"
            PostgreSQL: "TIMESTAMP '{{ value.strftime('%Y-%m-%d %H:%M:%S') }}'"
            BigQuery: "TIMESTAMP '{{ value.strftime('%Y-%m-%d %H:%M:%S') }}'"

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
            value (str): The regex pattern string.

        Examples:
            Snowflake: "'{{ value }}'"
            PostgreSQL: "'{{ value }}'"
            BigQuery: "r'{{ value }}'"

        Enables: regex pattern literals in filter predicates
        """
        pass

    def literal_table_from_value_list_template(self) -> str:
        """Return a Jinja template string for creating an inline table from a list of values.

        Jinja variables:
            values (list[str]): SQL literal values to form rows.

        Examples:
            Snowflake: "SELECT column1 AS value FROM VALUES {{ values | join(', ') }}"
            PostgreSQL: "SELECT unnest(ARRAY[{{ values | join(', ') }}]) AS value"
            BigQuery: "SELECT value FROM UNNEST([{{ values | join(', ') }}]) AS value"

        Enables: IN/NOT IN list predicates
        """
        pass

    def date_literal_template(self) -> str:
        """Return a Jinja template string for a SQL DATE literal.

        Jinja variables:
            value (date): Python date to render as SQL literal.

        Examples:
            Snowflake: "DATE '{{ value.strftime('%Y-%m-%d') }}'"
            PostgreSQL: "DATE '{{ value.strftime('%Y-%m-%d') }}'"
            BigQuery: "DATE '{{ value.strftime('%Y-%m-%d') }}'"

        Enables: date literal values
        """
        pass

    def utc_literal_template(self) -> str:
        """Return a Jinja template string for a UTC timestamp literal.

        Jinja variables:
            value (datetime): Python datetime to render as UTC SQL literal.

        Examples:
            Snowflake: "TIMESTAMP '{{ value.strftime('%Y-%m-%d %H:%M:%S') }}' ::TIMESTAMP_TZ"
            PostgreSQL: "TIMESTAMP WITH TIME ZONE '{{ value.strftime('%Y-%m-%d %H:%M:%S') }}+00'"
            BigQuery: "TIMESTAMP '{{ value.strftime('%Y-%m-%d %H:%M:%S') }} UTC'"

        Enables: UTC timestamp literal values
        """
        pass

    ###################################################
    # QueryLanguage: Type Casting
    ###################################################
    def get_casting_to_numeric_expression_template(self) -> str:
        """Return a Jinja template string for casting a field to a numeric type.

        Jinja variables:
            field (str): Column name or expression to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS NUMERIC)"
            PostgreSQL: "CAST({{ field }} AS NUMERIC)"
            BigQuery: "CAST({{ field }} AS NUMERIC)"

        Enables: rate denominator for all *_rate metrics
        """
        pass

    def cast_to_string_func_template(self) -> str:
        """Return a Jinja template string for casting a field to string/varchar.

        Jinja variables:
            field (str): Column name or expression to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS VARCHAR)"
            PostgreSQL: "CAST({{ field }} AS TEXT)"
            BigQuery: "CAST({{ field }} AS STRING)"

        Enables: string conversions for timestamp and JSON operations
        """
        pass

    def get_casting_to_decimal_expression_template(self) -> str:
        """Return a Jinja template string for casting a field to decimal with precision.

        Jinja variables:
            field (str): Column name or expression to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS DECIMAL(38, 10))"
            PostgreSQL: "CAST({{ field }} AS DECIMAL(38, 10))"
            BigQuery: "CAST({{ field }} AS BIGNUMERIC)"

        Enables: sum metric
        """
        pass

    def default_cast_to_timestamp_func_template(self) -> str:
        """Return a Jinja template string for casting a value to timestamp (default/fallback).

        Jinja variables:
            field (str): Value or column to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS TIMESTAMP)"
            PostgreSQL: "CAST({{ field }} AS TIMESTAMP)"
            BigQuery: "CAST({{ field }} AS TIMESTAMP)"

        Enables: time range filters when field type is unknown
        """
        pass

    def cast_string_to_timestamp_template(self) -> str:
        """Return a Jinja template string for casting a string value to timestamp.

        Jinja variables:
            field (str): String expression to cast.

        Examples:
            Snowflake: "TRY_CAST({{ field }} AS TIMESTAMP)"
            PostgreSQL: "{{ field }}::TIMESTAMP"
            BigQuery: "SAFE_CAST({{ field }} AS TIMESTAMP)"

        Enables: timestamp casting for string-typed time fields
        """
        pass

    def cast_numeric_to_timestamp_template(self) -> str:
        """Return a Jinja template string for casting a numeric (epoch) value to timestamp.

        Jinja variables:
            field (str): Numeric expression to cast.

        Examples:
            Snowflake: "TO_TIMESTAMP({{ field }})"
            PostgreSQL: "TO_TIMESTAMP({{ field }})"
            BigQuery: "TIMESTAMP_SECONDS(CAST({{ field }} AS INT64))"

        Enables: timestamp casting for epoch-typed time fields
        """
        pass

    def cast_date_to_timestamp_template(self) -> str:
        """Return a Jinja template string for casting a date value to timestamp.

        Jinja variables:
            field (str): Date expression to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS TIMESTAMP)"
            PostgreSQL: "{{ field }}::TIMESTAMP"
            BigQuery: "CAST({{ field }} AS TIMESTAMP)"

        Enables: timestamp casting for date-typed time fields
        """
        pass

    def cast_default_to_timestamp_template(self) -> str:
        """Return a Jinja template string for default timestamp casting when type is unknown.

        Jinja variables:
            field (str): Expression to cast.

        Examples:
            Snowflake: "TRY_CAST({{ field }} AS TIMESTAMP)"
            PostgreSQL: "CAST({{ field }} AS TIMESTAMP)"
            BigQuery: "SAFE_CAST({{ field }} AS TIMESTAMP)"

        Enables: fallback timestamp casting
        """
        pass

    def cast_timestamp_to_date_template(self) -> str:
        """Return a Jinja template string for casting a timestamp to date type.

        Jinja variables:
            field (str): Timestamp expression to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS DATE)"
            PostgreSQL: "{{ field }}::DATE"
            BigQuery: "CAST({{ field }} AS DATE)"

        Enables: timestamp-to-date conversion for filter predicates
        """
        pass

    def cast_timestamp_to_timestamp_ntz_template(self) -> str:
        """Return a Jinja template string for casting a timestamp to timestamp without timezone.

        Jinja variables:
            field (str): Timestamp expression to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS TIMESTAMP_NTZ)"
            PostgreSQL: "{{ field }}::TIMESTAMP WITHOUT TIME ZONE"
            BigQuery: "{{ field }}"

        Enables: timezone-naive timestamp comparisons
        """
        pass

    def cast_timestamp_to_timestamp_tz_template(self) -> str:
        """Return a Jinja template string for casting a timestamp to timestamp with timezone.

        Jinja variables:
            field (str): Timestamp expression to cast.

        Examples:
            Snowflake: "CAST({{ field }} AS TIMESTAMP_TZ)"
            PostgreSQL: "{{ field }}::TIMESTAMP WITH TIME ZONE"
            BigQuery: "{{ field }}"

        Enables: timezone-aware timestamp comparisons
        """
        pass

    def cast_to_timestamp_with_tz_template(self) -> str:
        """Return a Jinja template string rendering the timestamp-with-timezone type name.

        Jinja variables:
            None

        Examples:
            Snowflake: "TIMESTAMPTZ"
            PostgreSQL: "TIMESTAMP WITH TIME ZONE"
            BigQuery: "TIMESTAMP"

        Enables: timezone-aware timestamp casting
        """
        pass

    def cast_to_timestamp_without_tz_template(self) -> str:
        """Return a Jinja template string rendering the timestamp-without-timezone type name.

        Jinja variables:
            None

        Examples:
            Snowflake: "TIMESTAMP_NTZ"
            PostgreSQL: "TIMESTAMP WITHOUT TIME ZONE"
            BigQuery: "TIMESTAMP"

        Enables: timezone-naive timestamp casting
        """
        pass

    ###################################################
    # QueryLanguage: Date/Time Functions
    ###################################################
    def convert_to_utc_template(self) -> str:
        """Return a Jinja template string for converting a timezone-aware field to UTC.

        Jinja variables:
            field (str): Timestamp expression with timezone.

        Examples:
            Snowflake: "CONVERT_TIMEZONE('UTC', {{ field }})"
            PostgreSQL: "{{ field }} AT TIME ZONE 'UTC'"
            BigQuery: "TIMESTAMP({{ field }}, 'UTC')"

        Enables: UTC normalization for time range filters
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
            field (str): Date expression.
            days (int): Number of days to add (negative to subtract).

        Examples:
            Snowflake: "DATEADD(day, {{ days }}, {{ field }})"
            PostgreSQL: "{{ field }} + INTERVAL '{{ days }} days'"
            BigQuery: "DATE_ADD({{ field }}, INTERVAL {{ days }} DAY)"

        Enables: date arithmetic in time range filters
        """
        pass

    def add_days_timestamp_func_template(self) -> str:
        """Return a Jinja template string for adding/subtracting days from a timestamp.

        Jinja variables:
            field (str): Timestamp expression.
            days (int): Number of days to add (negative to subtract).

        Examples:
            Snowflake: "DATEADD(day, {{ days }}, {{ field }})"
            PostgreSQL: "{{ field }} + INTERVAL '{{ days }} days'"
            BigQuery: "TIMESTAMP_ADD({{ field }}, INTERVAL {{ days }} DAY)"

        Enables: timestamp arithmetic in time range filters
        """
        pass

    def add_hours_timestamp_func_template(self) -> str:
        """Return a Jinja template string for adding/subtracting hours from a timestamp.

        Jinja variables:
            field (str): Timestamp expression.
            hours (int): Number of hours to add (negative to subtract).

        Examples:
            Snowflake: "DATEADD(hour, {{ hours }}, {{ field }})"
            PostgreSQL: "{{ field }} + INTERVAL '{{ hours }} hours'"
            BigQuery: "TIMESTAMP_ADD({{ field }}, INTERVAL {{ hours }} HOUR)"

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

        Jinja variables:
            field (str): Timestamp expression to check.

        Examples:
            Snowflake: "CAST({{ field }} AS DATE) = DATEADD(day, -1, CURRENT_DATE)"
            PostgreSQL: "{{ field }}::DATE = CURRENT_DATE - INTERVAL '1 day'"
            BigQuery: "CAST({{ field }} AS DATE) = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)"

        Enables: yesterday filter in time range expressions
        """
        pass

    def get_in_past_days_expression_template(self) -> str:
        """Return a Jinja template string for checking if a timestamp is within the past N days.

        Jinja variables:
            field (str): Timestamp expression to check.
            days (int): Number of past days.

        Examples:
            Snowflake: "{{ field }} >= DATEADD(day, -{{ days }}, CURRENT_TIMESTAMP())"
            PostgreSQL: "{{ field }} >= NOW() - INTERVAL '{{ days }} days'"
            BigQuery: "{{ field }} >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {{ days }} DAY)"

        Enables: past-N-days time range filter
        """
        pass

    def get_in_past_hours_expression_template(self) -> str:
        """Return a Jinja template string for checking if a timestamp is within the past N hours.

        Jinja variables:
            field (str): Timestamp expression to check.
            hours (int): Number of past hours.

        Examples:
            Snowflake: "{{ field }} >= DATEADD(hour, -{{ hours }}, CURRENT_TIMESTAMP())"
            PostgreSQL: "{{ field }} >= NOW() - INTERVAL '{{ hours }} hours'"
            BigQuery: "{{ field }} >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {{ hours }} HOUR)"

        Enables: past-N-hours time range filter
        """
        pass

    def get_in_past_calendar_week_expression_template(self) -> str:
        """Return a Jinja template string for checking if a timestamp falls in the current calendar week.

        Jinja variables:
            field (str): Timestamp expression to check.

        Examples:
            Snowflake: "DATE_TRUNC('WEEK', {{ field }}) = DATE_TRUNC('WEEK', CURRENT_DATE)"
            PostgreSQL: "DATE_TRUNC('week', {{ field }}) = DATE_TRUNC('week', CURRENT_DATE)"
            BigQuery: "TIMESTAMP_TRUNC({{ field }}, WEEK) = TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), WEEK)"

        Enables: calendar week filter
        """
        pass

    def get_in_past_calendar_month_expression_template(self) -> str:
        """Return a Jinja template string for checking if a timestamp falls in the current calendar month.

        Jinja variables:
            field (str): Timestamp expression to check.

        Examples:
            Snowflake: "DATE_TRUNC('MONTH', {{ field }}) = DATE_TRUNC('MONTH', CURRENT_DATE)"
            PostgreSQL: "DATE_TRUNC('month', {{ field }}) = DATE_TRUNC('month', CURRENT_DATE)"
            BigQuery: "TIMESTAMP_TRUNC({{ field }}, MONTH) = TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), MONTH)"

        Enables: calendar month filter
        """
        pass

    def get_date_diff_func_template(self) -> str:
        """Return a Jinja template string for computing the difference between two dates/timestamps.

        Jinja variables:
            field1 (str): Start date/timestamp.
            field2 (str): End date/timestamp.
            unit (str): Unit of difference (e.g. 'day', 'hour').

        Examples:
            Snowflake: "DATEDIFF({{ unit }}, {{ field1 }}, {{ field2 }})"
            PostgreSQL: "EXTRACT(EPOCH FROM ({{ field2 }} - {{ field1 }})) / 86400"
            BigQuery: "DATE_DIFF({{ field2 }}, {{ field1 }}, DAY)"

        Enables: date/timestamp difference in comparison monitors
        """
        pass

    def get_days_of_week_expression_template(self) -> str:
        """Return a Jinja template string for extracting the day of week from a timestamp.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake: "DAYOFWEEK({{ field }})"
            PostgreSQL: "EXTRACT(DOW FROM {{ field }})"
            BigQuery: "EXTRACT(DAYOFWEEK FROM {{ field }})"

        Enables: day-of-week filtering
        """
        pass

    def convert_to_unix_timestamp_func_template(self) -> str:
        """Return a Jinja template string for converting a field to Unix epoch seconds.

        Jinja variables:
            field (str): Timestamp expression to convert.

        Examples:
            Snowflake: "EXTRACT(EPOCH FROM {{ field }})"
            PostgreSQL: "EXTRACT(EPOCH FROM {{ field }})"
            BigQuery: "UNIX_SECONDS({{ field }})"

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
        """Return a Jinja template string rendering "true" or "false" for literal GROUP BY support.

        Jinja variables:
            None

        Examples:
            Snowflake: "true"
            PostgreSQL: "true"
            BigQuery: "true"

        Enables: dialect flag for GROUP BY with literals
        """
        pass

    def supports_group_by_on_subquery_template(self) -> str:
        """Return a Jinja template string rendering "true" or "false" for GROUP BY on subquery support.

        Jinja variables:
            None

        Examples:
            Snowflake: "true"
            PostgreSQL: "true"
            BigQuery: "true"

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

    ###################################################
    # QueryLanguage: Null and NaN Handling
    ###################################################
    def is_null_template(self) -> str:
        """Return a Jinja template string for an IS NULL check.

        Jinja variables:
            field (str): Expression to check.

        Examples:
            Snowflake: "{{ field }} IS NULL"
            PostgreSQL: "{{ field }} IS NULL"
            BigQuery: "{{ field }} IS NULL"

        Enables: null-check filter predicates
        """
        pass

    def is_not_null_template(self) -> str:
        """Return a Jinja template string for an IS NOT NULL check.

        Jinja variables:
            field (str): Expression to check.

        Examples:
            Snowflake: "{{ field }} IS NOT NULL"
            PostgreSQL: "{{ field }} IS NOT NULL"
            BigQuery: "{{ field }} IS NOT NULL"

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

        Jinja variables:
            field (str): Expression to check for NaN.

        Examples:
            Snowflake: "{{ field }} != {{ field }}"
            PostgreSQL: "{{ field }} = 'NaN'::NUMERIC"
            BigQuery: "IS_NAN({{ field }})"

        Enables: nan_count metric, nan_rate metric
        """
        pass

    ###################################################
    # QueryLanguage: Comparison Operators
    ###################################################
    def get_is_eq_expression_template(self) -> str:
        """Return a Jinja template string for equality comparison.

        Jinja variables:
            field1 (str): Left operand.
            field2 (str): Right operand.

        Examples:
            Snowflake: "{{ field1 }} = {{ field2 }}"
            PostgreSQL: "{{ field1 }} = {{ field2 }}"
            BigQuery: "{{ field1 }} = {{ field2 }}"

        Enables: threshold and custom rule evaluation in comparison monitors
        """
        pass

    def get_is_gt_expression_template(self) -> str:
        """Return a Jinja template string for greater-than comparison.

        Jinja variables:
            field1 (str): Left operand.
            field2 (str): Right operand.

        Examples:
            Snowflake: "{{ field1 }} > {{ field2 }}"
            PostgreSQL: "{{ field1 }} > {{ field2 }}"
            BigQuery: "{{ field1 }} > {{ field2 }}"

        Enables: threshold comparisons in comparison monitors
        """
        pass

    def get_is_gte_expression_template(self) -> str:
        """Return a Jinja template string for greater-than-or-equal comparison.

        Jinja variables:
            field1 (str): Left operand.
            field2 (str): Right operand.

        Examples:
            Snowflake: "{{ field1 }} >= {{ field2 }}"
            PostgreSQL: "{{ field1 }} >= {{ field2 }}"
            BigQuery: "{{ field1 }} >= {{ field2 }}"

        Enables: threshold comparisons in comparison monitors
        """
        pass

    def get_is_lt_expression_template(self) -> str:
        """Return a Jinja template string for less-than comparison.

        Jinja variables:
            field1 (str): Left operand.
            field2 (str): Right operand.

        Examples:
            Snowflake: "{{ field1 }} < {{ field2 }}"
            PostgreSQL: "{{ field1 }} < {{ field2 }}"
            BigQuery: "{{ field1 }} < {{ field2 }}"

        Enables: range checks in comparison monitors
        """
        pass

    def get_is_lte_expression_template(self) -> str:
        """Return a Jinja template string for less-than-or-equal comparison.

        Jinja variables:
            field1 (str): Left operand.
            field2 (str): Right operand.

        Examples:
            Snowflake: "{{ field1 }} <= {{ field2 }}"
            PostgreSQL: "{{ field1 }} <= {{ field2 }}"
            BigQuery: "{{ field1 }} <= {{ field2 }}"

        Enables: range checks in comparison monitors
        """
        pass

    def get_is_inside_range_expression_template(self) -> str:
        """Return a Jinja template string for checking if a value is inside a range (inclusive).

        Jinja variables:
            field (str): Expression to check.
            lower (str): Lower bound.
            upper (str): Upper bound.

        Examples:
            Snowflake: "{{ field }} >= {{ lower }} AND {{ field }} <= {{ upper }}"
            PostgreSQL: "{{ field }} >= {{ lower }} AND {{ field }} <= {{ upper }}"
            BigQuery: "{{ field }} BETWEEN {{ lower }} AND {{ upper }}"

        Enables: range-based custom rule evaluation
        """
        pass

    def get_is_outside_range_expression_template(self) -> str:
        """Return a Jinja template string for checking if a value is outside a range.

        Jinja variables:
            field (str): Expression to check.
            lower (str): Lower bound.
            upper (str): Upper bound.

        Examples:
            Snowflake: "{{ field }} < {{ lower }} OR {{ field }} > {{ upper }}"
            PostgreSQL: "{{ field }} < {{ lower }} OR {{ field }} > {{ upper }}"
            BigQuery: "NOT ({{ field }} BETWEEN {{ lower }} AND {{ upper }})"

        Enables: range-based custom rule evaluation
        """
        pass

    ###################################################
    # QueryLanguage: Aggregation Functions
    ###################################################
    def get_avg_function_template(self) -> str:
        """Return a Jinja template string for the SQL AVG() aggregate function.

        Jinja variables:
            field (str): Column name or expression to average.

        Examples:
            Snowflake: "AVG({{ field }})"
            PostgreSQL: "AVG({{ field }})"
            BigQuery: "AVG({{ field }})"

        Enables: numeric_mean metric
        """
        pass

    def get_stddev_function_template(self) -> str:
        """Return a Jinja template string for the SQL standard deviation function.

        Jinja variables:
            field (str): Column name or expression.

        Examples:
            Snowflake: "STDDEV({{ field }})"
            PostgreSQL: "STDDEV_SAMP({{ field }})"
            BigQuery: "STDDEV({{ field }})"

        Enables: numeric_stddev metric, text_std_length metric
        """
        pass

    def get_distinct_count_func_template(self) -> str:
        """Return a Jinja template string for COUNT(DISTINCT ...).

        Jinja variables:
            field (str): Column name or expression to count distinct values of.

        Examples:
            Snowflake: "COUNT(DISTINCT {{ field }})"
            PostgreSQL: "COUNT(DISTINCT {{ field }})"
            BigQuery: "COUNT(DISTINCT {{ field }})"

        Enables: approx_distinct_count metric, approx_distinctness metric
        """
        pass

    def get_distinct_func_template(self) -> str:
        """Return a Jinja template string for a DISTINCT expression.

        Jinja variables:
            field (str): Column name or expression.

        Examples:
            Snowflake: "DISTINCT {{ field }}"
            PostgreSQL: "DISTINCT {{ field }}"
            BigQuery: "DISTINCT {{ field }}"

        Enables: distinctness queries
        """
        pass

    def get_safe_divide_template(self) -> str:
        """Return a Jinja template string for zero-safe division.

        Jinja variables:
            numerator (str): Numerator expression.
            denominator (str): Denominator expression.

        Examples:
            Snowflake: "DIV0({{ numerator }}, {{ denominator }})"
            PostgreSQL: "CASE WHEN {{ denominator }} = 0 THEN NULL ELSE {{ numerator }} / {{ denominator }} END"
            BigQuery: "SAFE_DIVIDE({{ numerator }}, {{ denominator }})"

        Enables: rate_count_if, capped_rate_sql calculations
        """
        pass

    def get_conditional_count_expression_template(self) -> str:
        """Return a Jinja template string for counting rows matching a condition.

        Jinja variables:
            condition (str): Boolean expression for counting.

        Examples:
            Snowflake: "COUNT_IF({{ condition }})"
            PostgreSQL: "COUNT(CASE WHEN {{ condition }} THEN 1 END)"
            BigQuery: "COUNTIF({{ condition }})"

        Enables: zero_count, negative_count, nan_count, empty_string_count, true_count, false_count metrics
        """
        pass

    def get_approx_quantiles_func_template(self) -> str:
        """Return a Jinja template string for approximate quantile buckets.

        Jinja variables:
            field (str): Column name or expression.
            num_buckets (int): Number of quantile buckets.

        Examples:
            Snowflake: "APPROX_PERCENTILE({{ field }}, 0.5)"
            PostgreSQL: "PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {{ field }})"
            BigQuery: "APPROX_QUANTILES({{ field }}, {{ num_buckets }})"

        Enables: approx_quantiles metric
        """
        pass

    def get_approx_percentile_func_template(self) -> str:
        """Return a Jinja template string for approximate percentile calculation.

        Jinja variables:
            field (str): Column name or expression.
            percentile (float): Percentile value between 0 and 1.

        Examples:
            Snowflake: "APPROX_PERCENTILE({{ field }}, {{ percentile }})"
            PostgreSQL: "PERCENTILE_CONT({{ percentile }}) WITHIN GROUP (ORDER BY {{ field }})"
            BigQuery: "APPROX_QUANTILES({{ field }}, 100)[OFFSET(CAST({{ percentile }} * 100 AS INT64))]"

        Enables: numeric_median, percentile_20/40/60/80 metrics
        """
        pass

    def approx_distinct_func_template(self) -> str:
        """Return a Jinja template string for approximate distinct count.

        Jinja variables:
            field (str): Column name or expression.

        Examples:
            Snowflake: "APPROX_COUNT_DISTINCT({{ field }})"
            PostgreSQL: "COUNT(DISTINCT {{ field }})"
            BigQuery: "APPROX_COUNT_DISTINCT({{ field }})"

        Enables: approximate unique count
        """
        pass

    def any_value_template(self) -> str:
        """Return a Jinja template string for an ANY_VALUE() aggregate.

        Jinja variables:
            field (str): Column name or expression.

        Examples:
            Snowflake: "ANY_VALUE({{ field }})"
            PostgreSQL: "MIN({{ field }})"
            BigQuery: "ANY_VALUE({{ field }})"

        Enables: comparison monitor GROUP BY queries
        """
        pass

    ###################################################
    # QueryLanguage: String Functions
    ###################################################
    def get_length_template(self) -> str:
        """Return a Jinja template string for string length.

        Jinja variables:
            field (str): String expression to measure.

        Examples:
            Snowflake: "LENGTH({{ field }})"
            PostgreSQL: "LENGTH({{ field }})"
            BigQuery: "LENGTH({{ field }})"

        Enables: text_mean_length, text_min_length, text_max_length, text_std_length metrics
        """
        pass

    def substring_func_template(self) -> str:
        """Return a Jinja template string for substring extraction.

        Jinja variables:
            field (str): String expression.
            start (int): Starting position (1-indexed).
            length (int): Number of characters to extract.

        Examples:
            Snowflake: "SUBSTR({{ field }}, {{ start }}, {{ length }})"
            PostgreSQL: "SUBSTRING({{ field }} FROM {{ start }} FOR {{ length }})"
            BigQuery: "SUBSTR({{ field }}, {{ start }}, {{ length }})"

        Enables: substring extraction
        """
        pass

    def get_is_empty_string_expression_template(self) -> str:
        """Return a Jinja template string for checking if a field is an empty string.

        Jinja variables:
            field (str): String expression to check.

        Examples:
            Snowflake: "{{ field }} = ''"
            PostgreSQL: "{{ field }} = ''"
            BigQuery: "{{ field }} = ''"

        Enables: empty_string_count metric, empty_string_rate metric
        """
        pass

    def get_regexp_expression_template(self) -> str:
        """Return a Jinja template string for regex matching expression.

        Jinja variables:
            field (str): String expression to match.
            pattern (str): Regex pattern.

        Examples:
            Snowflake: "REGEXP_LIKE({{ field }}, {{ pattern }})"
            PostgreSQL: "{{ field }} ~ {{ pattern }}"
            BigQuery: "REGEXP_CONTAINS({{ field }}, {{ pattern }})"

        Enables: regex filter predicates, sampling
        """
        pass

    def get_regexp_count_expression_template(self) -> str:
        """Return a Jinja template string for counting regex matches within a string.

        Jinja variables:
            field (str): String expression to search.
            pattern (str): Regex pattern to count matches of.

        Examples:
            Snowflake: "REGEXP_COUNT({{ field }}, {{ pattern }})"
            PostgreSQL: "(SELECT COUNT(*) FROM REGEXP_MATCHES({{ field }}, {{ pattern }}, 'g'))"
            BigQuery: "ARRAY_LENGTH(REGEXP_EXTRACT_ALL({{ field }}, {{ pattern }}))"

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

        Jinja variables:
            field (str): Array expression.

        Examples:
            Snowflake: "ARRAY_SIZE({{ field }})"
            PostgreSQL: "ARRAY_LENGTH({{ field }}, 1)"
            BigQuery: "ARRAY_LENGTH({{ field }})"

        Enables: array_null_rate metric
        """
        pass

    def get_is_timestamp_expression_template(self) -> str:
        """Return a Jinja template string for checking if a string is a valid timestamp.

        Jinja variables:
            field (str): String expression to validate.

        Examples:
            Snowflake: "TRY_CAST({{ field }} AS TIMESTAMP) IS NOT NULL"
            PostgreSQL: "{{ field }}::TIMESTAMP IS NOT NULL"
            BigQuery: "SAFE_CAST({{ field }} AS TIMESTAMP) IS NOT NULL"

        Enables: text_timestamp_count metric, text_timestamp_rate metric
        """
        pass

    def get_not_is_timestamp_expression_template(self) -> str:
        """Return a Jinja template string for checking if a string is NOT a valid timestamp.

        Jinja variables:
            field (str): String expression to validate.

        Examples:
            Snowflake: "TRY_CAST({{ field }} AS TIMESTAMP) IS NULL"
            PostgreSQL: "{{ field }}::TIMESTAMP IS NULL"
            BigQuery: "SAFE_CAST({{ field }} AS TIMESTAMP) IS NULL"

        Enables: text_not_timestamp_count metric
        """
        pass

    def get_epoch_seconds_expression_template(self) -> str:
        """Return a Jinja template string for extracting epoch seconds from a timestamp.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake: "EXTRACT(EPOCH FROM {{ field }})"
            PostgreSQL: "EXTRACT(EPOCH FROM {{ field }})"
            BigQuery: "UNIX_SECONDS({{ field }})"

        Enables: past_timestamp_count, future_timestamp_count, unix_zero_count metrics
        """
        pass

    def get_epoch_seconds_parameter_template(self) -> str:
        """Return a Jinja template string for epoch seconds parameter.

        Jinja variables:
            field (str): Timestamp expression.

        Examples:
            Snowflake: "EXTRACT(EPOCH FROM {{ field }})"
            PostgreSQL: "EXTRACT(EPOCH FROM {{ field }})"
            BigQuery: "UNIX_SECONDS({{ field }})"

        Enables: epoch seconds parameter extraction
        """
        pass

    ###################################################
    # QueryLanguage: Math Functions
    ###################################################
    def get_absolute_value_function_template(self) -> str:
        """Return a Jinja template string for absolute value.

        Jinja variables:
            field (str): Numeric expression.

        Examples:
            Snowflake: "ABS({{ field }})"
            PostgreSQL: "ABS({{ field }})"
            BigQuery: "ABS({{ field }})"

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
            query (str): Source query or table.
            columns (list[str]): Column names to unpivot.
            name_column (str): Name for the unpivoted column name field.
            value_column (str): Name for the unpivoted value field.

        Examples:
            Snowflake: "SELECT * FROM ({{ query }}) UNPIVOT ({{ value_column }} FOR {{ name_column }} IN ({{ columns | join(', ') }}))"
            PostgreSQL: "SELECT {{ name_column }}, {{ value_column }} FROM ({{ query }}) src CROSS JOIN LATERAL (VALUES ...) AS unpivoted({{ name_column }}, {{ value_column }})"
            BigQuery: "SELECT * FROM ({{ query }}) UNPIVOT ({{ value_column }} FOR {{ name_column }} IN ({{ columns | join(', ') }}))"

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
