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
def database(integration, templates) -> str:
    query = templates.render_template(
        templates.get_databases_query_template,
    )
    results = integration.execute_and_fetch_all(query)

    return results[0][0]


@pytest.fixture(scope="session")
def schemas(integration, templates, database) -> List[str]:
    query = templates.render_template(
        templates.get_schemas_query_template,
        database_name=database
    )
    results = integration.execute_and_fetch_all(query)

    return [row[0] for row in results[:5]]


@pytest.fixture(scope="session")
def tables(integration, templates, database, schemas) -> List[MetadataSchema]:
    offset = 0
    limit = 5000
    query = templates.render_template(
        templates.get_tables_query_template,
        database_name=database,
        schemas=", ".join([f"'{sch}'" for sch in schemas]),
        offset=offset,
        limit=limit,
    )
    results = integration.execute_and_fetch_all(query)
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
        if byte_count := plugin_table.byte_count:
            assert isinstance(byte_count, int), f"Byte count should be an int but returned {type(byte_count)} for table {plugin_table.full_table_id}"
        if last_update_time := plugin_table.last_update_time:
            assert isinstance(last_update_time, datetime), f"Last_update_time should be a datetime but returned {type(last_update_time)} for table {plugin_table.full_table_id}"
        if view_query := plugin_table.view_query:
            assert plugin_table.table_type == 'view', f"A view_query was returned for the table {plugin_table.full_table_id}"
            assert isinstance(view_query, str), f"View_query should be a string but returned a {type(view_query)} for view {plugin_table.full_table_id}"

        plugin_tables.append(plugin_table)

    return plugin_tables


#############################################
# Metadata Related Tests
#############################################
@pytest.mark.template(
    file="fetch_databases_query.sql.j2",
    fixture="integration",
    func="get_databases_query_template"
)
def test_fetch_databases(database):
    assert database, "Failed to fetch databases"


@pytest.mark.template(
    file="fetch_schemas_query.sql.j2",
    fixture="integration",
    func="get_schemas_query_template"
)
def test_fetch_schemas(database, schemas):
    assert schemas, f"Failed to fetch schemas for database {database}"


@pytest.mark.template(
    file="fetch_tables_query.sql.j2",
    fixture="integration",
    func="get_tables_query_template"
)
@pytest.mark.capability("supports_metadata")
def test_fetch_tables_and_views(integration, database, schemas, tables):
    assert tables, f"Failed to fetch tables for database {database} and schemas {', '.join(schemas)}"


@pytest.mark.template(
    file="fetch_tables_query.sql.j2",
    fixture="integration",
    func="get_tables_query_template"
)
@pytest.mark.capability("supports_metadata")
def test_fetch_tables_with_table_names_filter(integration, templates, database, schemas, tables):
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
    results = integration.execute_and_fetch_all(query)

    expected_names = {t.table_name.lower() for t in sample_tables}
    returned_names = set()
    for row in results:
        parsed = MetadataSchema(*row)
        returned_names.add(parsed.table_name.lower())

    assert returned_names == expected_names, (
        f"table_names filter did not return the expected tables. "
        f"Expected: {sorted(expected_names)}, Got: {sorted(returned_names)}"
    )


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
    fixture="integration",
    func="get_columns_query_template"
)
def test_fetch_columns(integration, templates, database, tables):
    query = templates.render_template(
        templates.get_columns_query_template,
        tables=", ".join([f"'{table.full_table_id}'" for table in tables]),
        database_name=database
    )
    results = integration.execute_and_fetch_all(query)
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
# Query Log Related Tests
#############################################
@pytest.mark.capability("supports_query_logs", "supports_lineage", "supports_field_lineage")
@pytest.mark.template(
    file="fetch_query_logs_query.sql.j2",
    fixture="integration",
    func="get_query_logs_query_template"
)
def test_get_query_logs(integration, templates):
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
    results = integration.execute_and_fetch_all(query)
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
