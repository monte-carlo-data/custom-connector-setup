from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import pytest
from dataclasses_json import DataClassJsonMixin

pytestmark = [pytest.mark.metadata]


#############################################
# Data classes
#############################################
@dataclass
class ParsedMCON:
    account_id: UUID
    resource_id: UUID
    object_type: str
    object_id: str

    def __str__(self):
        return self.create_mcon(
            self.account_id, self.resource_id, self.object_type, self.object_id
        )

    @staticmethod
    def create_mcon(account_id: UUID, resource_id: UUID, object_type: str, object_id: str) -> str:
        for arg, value in [
            ("account_id", account_id),
            ("resource_id", resource_id),
            ("object_type", object_type),
            ("object_id", object_id),
        ]:
            if value is None:
                raise ValueError(f"{arg} is None, cannot create MCON")
        return f"MCON++{account_id}++{resource_id}++{object_type.lower()}++{object_id}"

    @property
    def is_table_type(self) -> bool:
        """Get if parsed object is a table type."""
        return self.object_type.lower() in [
            "table", "view", "external", "wildcard_table", "temp-table", "vector-index", "dynamic"
        ]


@dataclass
class SchemaItem(DataClassJsonMixin):
    name: str
    type: str


@dataclass
class PluginQueryLog(DataClassJsonMixin):
    query_id: str
    start_time: datetime
    end_time: datetime
    query_text: str
    user: Optional[str] = None
    error_code: Optional[str] = None
    error_text: Optional[str] = None
    returned_rows: Optional[int] = None
    extra: Dict[str, Optional[Any]] = field(default_factory=dict)


@dataclass
class MetadataSchema(DataClassJsonMixin):
    database_name: str
    schema_name: str
    table_name: str
    table_type: str
    row_count: Optional[int] = None
    byte_count: Optional[int] = None
    last_update_time: Optional[datetime] = None
    view_query: Optional[str] = None
    schema: Optional[List[SchemaItem]] = None

    @property
    def full_table_id(self):
        return f"{self.database_name}.{self.schema_name}.{self.table_name}"


#############################################
# Add Metadata Fixtures
#############################################
@pytest.fixture(scope="session")
def database(connector, templates) -> str:
    query = templates.render_template(
        templates.get_databases_query_template,
    )
    results = connector.execute_and_fetch_all(query)

    return results[0][0]


@pytest.fixture(scope="session")
def schemas(connector, templates, database) -> List[str]:
    query = templates.render_template(
        templates.get_schemas_query_template,
        database_name=database
    )
    results = connector.execute_and_fetch_all(query)

    return [row[0] for row in results[:5]]


@pytest.fixture(scope="session")
def tables(connector, templates, database, schemas) -> List[MetadataSchema]:
    offset = 0
    limit = 5000
    query = templates.render_template(
        templates.get_tables_query_template,
        database_name=database,
        schemas=", ".join([f"'{sch}'" for sch in schemas]),
        offset=offset,
        limit=limit,
    )
    results = connector.execute_and_fetch_all(query)
    assert len(results) > 0, f"No tables found for database {database} for schemas {', '.join(schemas)}"
    assert len(results) <= limit, f"Table results should be limited to {limit} but {len(results)} were returned."

    plugin_tables = []
    for table in results:
        plugin_table = MetadataSchema(*table)

        # Required fields
        assert isinstance(plugin_table.database_name, str)
        assert isinstance(plugin_table.schema_name, str)
        assert isinstance(plugin_table.table_name, str)
        assert isinstance(plugin_table.table_type, str)
        assert plugin_table.table_type in ('table', 'view')

        # Optional fields
        if row_count := plugin_table.row_count:
            assert isinstance(row_count, int), f"Row count should be an int but returned {type(row_count)} for table {plugin_table.full_table_id}"
            assert row_count >= 0, f"Row count should not be negative but returned {row_count} for table {plugin_table.full_table_id}"
        if byte_count := plugin_table.byte_count:
            assert isinstance(byte_count, int), f"Byte count should be an int but returned {type(byte_count)} for table {plugin_table.full_table_id}"
        if last_update_time := plugin_table.last_update_time:
            if isinstance(last_update_time, str):
                try:
                    datetime.fromisoformat(last_update_time)
                except ValueError:
                    pytest.fail(f"Last_update_time string is not ISO 8601 parseable: '{last_update_time}' for table {plugin_table.full_table_id}")
            else:
                assert isinstance(last_update_time, datetime), f"Last_update_time should be a datetime or ISO 8601 string but returned {type(last_update_time)} for table {plugin_table.full_table_id}"
        if view_query := plugin_table.view_query:
            assert plugin_table.table_type == 'view', f"A view_query was returned for the table {plugin_table.full_table_id}"
            assert isinstance(view_query, str), f"View_query should be a string but returned a {type(view_query)} for view {plugin_table.full_table_id}"

        plugin_tables.append(plugin_table)

    return plugin_tables


#############################################
# Column Name Contract Tests
#############################################
@pytest.mark.template(
    file="fetch_tables_query.sql.j2",
    fixture="connector",
    func="get_tables_query_template"
)
@pytest.mark.capability("supports_metadata")
def test_tables_column_names(connector, templates, database, schemas):
    """Verify get_tables cursor.description returns lowercase column names.

    The agent framework maps result columns by name (case-sensitive).
    Databases like Oracle return UPPERCASE column names by default, which
    silently produces empty metadata in production while tests that only
    use positional unpacking still pass.
    """
    query = templates.render_template(
        templates.get_tables_query_template,
        database_name=database,
        schemas=", ".join([f"'{sch}'" for sch in schemas]),
        offset=0,
        limit=1,
    )
    connector.execute_and_fetch_all(query)
    desc = connector.cursor.description
    assert desc is not None, "cursor.description is None after tables query"

    required_columns = {"database_name", "schema_name", "table_name", "table_type"}
    actual_columns = {col[0] for col in desc}
    missing = required_columns - actual_columns
    assert not missing, (
        f"get_tables_query_template cursor.description is missing required columns: {sorted(missing)}. "
        f"Actual columns: {sorted(actual_columns)}. "
        f"If your database returns UPPERCASE column names (e.g. Oracle), use double-quoted "
        f"aliases: SELECT col AS \"database_name\" to preserve lowercase."
    )


@pytest.mark.template(
    file="fetch_columns_query.sql.j2",
    fixture="connector",
    func="get_columns_query_template"
)
@pytest.mark.capability("supports_schema")
def test_columns_column_names(connector, templates, database, tables):
    """Verify get_columns cursor.description returns lowercase column names."""
    if not templates.get_columns_query_template():
        pytest.skip("get_columns_query_template not implemented")

    query = templates.render_template(
        templates.get_columns_query_template,
        tables=", ".join([f"'{table.full_table_id}'" for table in tables[:1]]),
        database_name=database,
    )
    results = connector.execute_and_fetch_all(query)
    if not results:
        pytest.skip("No columns returned to check column names")

    desc = connector.cursor.description
    required_columns = {"full_table_id", "column_name", "column_type"}
    actual_columns = {col[0] for col in desc}
    missing = required_columns - actual_columns
    assert not missing, (
        f"get_columns_query_template cursor.description is missing required columns: {sorted(missing)}. "
        f"Actual columns: {sorted(actual_columns)}. "
        f"Use double-quoted aliases to preserve lowercase if your database uppercases identifiers."
    )


#############################################
# Metadata Related Tests
#############################################
@pytest.mark.template(
    file="fetch_databases_query.sql.j2",
    fixture="connector",
    func="get_databases_query_template"
)
def test_fetch_databases(database):
    assert database, "Failed to fetch databases"


@pytest.mark.template(
    file="fetch_schemas_query.sql.j2",
    fixture="connector",
    func="get_schemas_query_template"
)
def test_fetch_schemas(database, schemas):
    assert schemas, f"Failed to fetch schemas for database {database}"


@pytest.mark.template(
    file="fetch_tables_query.sql.j2",
    fixture="connector",
    func="get_tables_query_template"
)
@pytest.mark.capability("supports_metadata")
def test_fetch_tables_and_views(connector, database, schemas, tables):
    assert tables, f"Failed to fetch tables for database {database} and schemas {', '.join(schemas)}"


@pytest.mark.template(
    file="fetch_tables_query.sql.j2",
    fixture="connector",
    func="get_tables_query_template"
)
@pytest.mark.capability("supports_metadata")
def test_fetch_tables_with_table_names_filter(connector, templates, database, schemas, tables):
    """Verify that providing table_names filters results to only those tables."""
    sample_tables = tables[:3]
    assert len(sample_tables) > 0, "Need at least one table to test table_names filter"

    table_names_param = ", ".join([f"'{t.table_name}'" for t in sample_tables])
    schemas_param = ", ".join([f"'{sch}'" for sch in schemas])

    query = templates.render_template(
        templates.get_tables_query_template,
        database_name=database,
        schemas=schemas_param,
        table_names=table_names_param,
        offset=0,
        limit=5000,
    )
    results = connector.execute_and_fetch_all(query)

    expected_names = {t.table_name.lower() for t in sample_tables}
    returned_names = set()
    for row in results:
        parsed = MetadataSchema(*row)
        returned_names.add(parsed.table_name.lower())

    assert returned_names == expected_names, (
        f"table_names filter did not return the expected tables. "
        f"Expected: {sorted(expected_names)}, Got: {sorted(returned_names)}"
    )


@pytest.mark.template(func="get_table_identifier_template")
def test_table_identifier_is_queryable(connector, templates, tables):
    """Verify that get_table_identifier_template produces an identifier the database accepts.

    The agent uses this identifier in every monitor query (e.g. SELECT ... FROM <identifier>).
    If the format is wrong (e.g. three-part naming on a database that doesn't support it),
    every monitor will fail at runtime. This test catches that early by picking a real table
    from metadata and executing a zero-row query against it.
    """
    # Pick a concrete table from metadata
    sample = next((t for t in tables if t.table_type == "table"), tables[0])

    identifier = templates.render_template(
        templates.get_table_identifier_template,
        _optional_vars={"database"},
        database=sample.database_name,
        schema=sample.schema_name,
        table=sample.table_name,
    )
    connector.execute_and_fetch_all(f"SELECT * FROM {identifier} WHERE 1=0")


@pytest.mark.capability("supports_volume_rows")
def test_volume_rows(tables):
    supports_rows = any(
        t.table_type == "table" and t.row_count is not None
        for t in tables
    )
    if not supports_rows:
        pytest.xfail("Optional feature: volume rows not supported")


@pytest.mark.capability("supports_volume_bytes")
def test_volume_bytes(tables):
    supports_bytes = any(
        t.table_type == 'table' and t.byte_count is not None
        for t in tables
    )
    if not supports_bytes:
        pytest.xfail("Optional feature: volume bytes not supported")


@pytest.mark.capability("supports_freshness")
def test_freshness(tables):
    supports_freshness = any(
        t.table_type == 'table' and t.last_update_time is not None
        for t in tables
    )
    if not supports_freshness:
        pytest.xfail("Optional feature: freshness not supported")


@pytest.mark.capability("supports_schema")
@pytest.mark.template(
    file="fetch_columns_query.sql.j2",
    fixture="connector",
    func="get_columns_query_template"
)
def test_fetch_columns(connector, templates, database, tables):
    query = templates.render_template(
        templates.get_columns_query_template,
        tables=", ".join([f"'{table.full_table_id}'" for table in tables]),
        database_name=database
    )
    results = connector.execute_and_fetch_all(query)
    assert len(results) > 0, "No columns returned — check that full_table_id format matches between get_tables and get_columns templates"

    matched_table_ids = set()
    for res in results:
        table_name, col_name, col_type = res
        assert isinstance(table_name, str), f"Fetching columns returned a table_name that is not a string. Table: {table_name}, Column_name: {col_name}, Column_type: {col_type}"
        assert isinstance(col_name, str), f"Fetching columns returned a column name that is not a string. Table: {table_name}, Column_name: {col_name}, Column_type: {col_type}"
        assert isinstance(col_type, str), f"Fetching columns returned a column type that is not a string. Table: {table_name}, Column_name: {col_name}, Column_type: {col_type}"
        table = next((t for t in tables if t.full_table_id == table_name), None)
        assert table is not None, (
            f"Column result full_table_id '{table_name}' did not match any table from get_tables. "
            f"Expected one of: {[t.full_table_id for t in tables[:5]]}"
        )
        matched_table_ids.add(table_name)
        if not table.schema:
            table.schema = []
        table.schema.append(SchemaItem(name=col_name, type=col_type))


#############################################
# Non-empty Value Contract Tests
#############################################
@pytest.mark.template(
    file="fetch_tables_query.sql.j2",
    fixture="connector",
    func="get_tables_query_template"
)
@pytest.mark.capability("supports_metadata")
def test_tables_required_fields_non_empty(tables):
    """Verify required metadata fields are non-empty strings.

    The existing tests check isinstance(field, str) but that also passes for
    empty strings. In production, empty database_name/schema_name/table_name
    renders the metadata useless.
    """
    for t in tables[:10]:
        assert t.database_name, (
            f"database_name is empty for table at position "
            f"({t.database_name!r}, {t.schema_name!r}, {t.table_name!r}). "
            f"Check your get_tables_query_template() SELECT column order."
        )
        assert t.schema_name, (
            f"schema_name is empty for {t.database_name}.*.{t.table_name}"
        )
        assert t.table_name, (
            f"table_name is empty for {t.database_name}.{t.schema_name}.*"
        )
        assert t.table_type, (
            f"table_type is empty for {t.full_table_id}"
        )


#############################################
# Query Log Related Tests
#############################################
@pytest.mark.capability("supports_query_logs", "supports_lineage", "supports_field_lineage")
@pytest.mark.template(
    file="fetch_query_logs_query.sql.j2",
    fixture="connector",
    func="get_query_logs_query_template"
)
def test_query_logs_column_names(connector, templates):
    """Verify get_query_logs cursor.description returns lowercase column names."""
    if not templates.get_query_logs_query_template():
        pytest.xfail("Optional feature: query log collection not implemented.")
    end_time = datetime.now(tz=UTC)
    start_time = end_time - timedelta(hours=1)
    query = templates.render_template(
        templates.get_query_logs_query_template,
        start_time=start_time,
        end_time=end_time,
        limit=1,
        offset=0,
    )
    connector.execute_and_fetch_all(query)
    desc = connector.cursor.description
    assert desc is not None, "cursor.description is None after query logs query"

    required_columns = {"query_id", "start_time", "end_time", "query_text"}
    actual_columns = {col[0] for col in desc}
    missing = required_columns - actual_columns
    assert not missing, (
        f"get_query_logs_query_template cursor.description is missing required columns: {sorted(missing)}. "
        f"Actual columns: {sorted(actual_columns)}. "
        f"Use double-quoted aliases to preserve lowercase if your database uppercases identifiers."
    )


@pytest.mark.capability("supports_query_logs", "supports_lineage", "supports_field_lineage")
@pytest.mark.template(
    file="fetch_query_logs_query.sql.j2",
    fixture="connector",
    func="get_query_logs_query_template"
)
def test_query_logs_with_string_timestamps(connector, templates):
    """Verify the query logs template works when start_time/end_time are strings.

    In production, the agent framework passes pre-formatted timestamp strings
    (e.g. '2024-01-15 10:30:00'), not Python datetime objects. Tests that only
    pass datetime objects miss template errors like calling .strftime() on a string.
    """
    if not templates.get_query_logs_query_template():
        pytest.xfail("Optional feature: query log collection not implemented.")

    # Use strings — this is what production passes
    end_time = datetime.now(tz=UTC)
    start_time_str = (end_time - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

    query = templates.render_template(
        templates.get_query_logs_query_template,
        start_time=start_time_str,
        end_time=end_time_str,
        limit=1,
        offset=0,
    )
    # If the template calls .strftime() on these strings, this will fail
    # with "'str' object has no attribute 'strftime'"
    results = connector.execute_and_fetch_all(query)
    assert isinstance(results, list), "Query log query should return a list"


@pytest.mark.capability("supports_query_logs", "supports_lineage", "supports_field_lineage")
@pytest.mark.template(
    file="fetch_query_logs_query.sql.j2",
    fixture="connector",
    func="get_query_logs_query_template"
)
def test_get_query_logs(connector, templates):
    if not templates.get_query_logs_query_template():
        pytest.xfail("Optional feature: query log collection not implemented.")
    end_time = datetime.now(tz=UTC)
    start_time = end_time - timedelta(hours=1)
    query = templates.render_template(
        templates.get_query_logs_query_template,
        start_time=start_time,
        end_time=end_time,
        limit=100,
        offset=0
    )
    results = connector.execute_and_fetch_all(query)
    assert len(results) > 0, f"No query logs retrieved from {start_time} to {end_time}"

    for row in results:
        assert len(row) >= 4, (
            f"Query log row must have at least 4 columns "
            f"(query_id, start_time, end_time, query_text), got {len(row)}"
        )
        log = PluginQueryLog(*row[:8])

        # Required fields
        assert isinstance(log.query_id, str), (
            f"query_id should be a str but got {type(log.query_id)}"
        )
        assert isinstance(log.start_time, datetime), (
            f"start_time should be a datetime but got {type(log.start_time)}"
        )
        assert isinstance(log.end_time, datetime), (
            f"end_time should be a datetime but got {type(log.end_time)}"
        )
        assert isinstance(log.query_text, str), (
            f"query_text should be a str but got {type(log.query_text)}"
        )

        # Optional fields
        if log.user is not None:
            assert isinstance(log.user, str), (
                f"user should be a str but got {type(log.user)}"
            )
        if log.error_code is not None:
            assert isinstance(log.error_code, str), (
                f"error_code should be a str but got {type(log.error_code)}"
            )
        if log.error_text is not None:
            assert isinstance(log.error_text, str), (
                f"error_text should be a str but got {type(log.error_text)}"
            )
        if log.returned_rows is not None:
            assert isinstance(log.returned_rows, int), (
                f"returned_rows should be an int but got {type(log.returned_rows)}"
            )
