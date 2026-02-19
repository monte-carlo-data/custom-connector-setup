from dataclasses import dataclass
from datetime import datetime, UTC, timedelta
from typing import List, Optional
from uuid import UUID

import pytest
from dataclasses_json import DataClassJsonMixin


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
# Create Fixtures
#############################################
@pytest.fixture(scope="session")
def database(integration) -> str:
    query = integration.render_template(
        integration.get_databases_query_template,
    )
    results = integration.execute_and_fetch_all(query)

    return results[0][0]


@pytest.fixture(scope="session")
def schemas(integration, database) -> List[str]:
    query = integration.render_template(
        integration.get_schemas_query_template,
        database_name=database
    )
    results = integration.execute_and_fetch_all(query)

    return [row[0] for row in results[:5]]


@pytest.fixture(scope="session")
def tables(integration, database, schemas) -> List[MetadataSchema]:
    offset = 0
    limit = 5000
    query = integration.render_template(
        integration.get_tables_query_template,
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
# Connection Related Tests
#############################################
def test_connection(integration):
    assert integration.connection, "Failed to make connection to database."


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
def test_fetch_tables_and_views(integration, database, schemas, tables):
    assert tables, f"Failed to fetch tables for database {database} and schemas {', '.join(schemas)}"


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
def test_fetch_columns(integration, database, tables):
    query = integration.render_template(
        integration.get_columns_query_template,
        tables=", ".join([f"'{table.full_table_id}'" for table in tables]),
        database_name=database
    )
    results = integration.execute_and_fetch_all(query)

    for res in results:
        table_name, col_name, col_type = res
        assert isinstance(table_name, str), f"Fetching columns returned a table_name that is not a string. Table: {table_name}, Column_name: {col_name}, Column_type: {col_type}"
        assert isinstance(col_name, str), f"Fetching columns returned a column name that is not a string. Table: {table_name}, Column_name: {col_name}, Column_type: {col_type}"
        assert isinstance(col_type, str), f"Fetching columns returned a column type that is not a string. Table: {table_name}, Column_name: {col_name}, Column_type: {col_type}"
        table = next((t for t in tables if t.full_table_id == table_name), None)
        if table:
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
def test_get_query_logs(integration):
    if not integration.get_query_logs_query_template():
        pytest.xfail("Optional feature: query log collection not implemented.")
    end_time = datetime.now(tz=UTC)
    start_time = end_time - timedelta(hours=1)
    query = integration.render_template(
        integration.get_query_logs_query_template,
        start_time=start_time,
        end_time=end_time
    )
    results = integration.execute_and_fetch_all(query)
    assert len(results) > 0, f"No query logs retrieved from {start_time} to {end_time}"
