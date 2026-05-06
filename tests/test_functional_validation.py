import time
from datetime import datetime, UTC, timedelta
from typing import List, Optional

import pytest

from tests.test_metadata_collection import MetadataSchema, SchemaItem

pytestmark = [pytest.mark.functional]


#############################################
# Helpers
#############################################
def table_vars(functional_ops) -> dict:
    """Return the Jinja variables for the test table identity."""
    database, schema, table = functional_ops.get_test_table_identifier()
    return {"database": database, "schema": schema, "table": table}


def render_functional(templates, template_method, functional_ops, **extra) -> str:
    """Render a functional test template with the table identity variables."""
    kwargs = table_vars(functional_ops)
    kwargs.update(extra)
    # database is optional context — not all databases need it in DDL
    return templates.render_template(template_method, _optional_vars={"database"}, **kwargs)


def collect_metadata(connector, templates, database, schemas, table_names=None) -> List[MetadataSchema]:
    """Run the get_tables_query_template and return parsed MetadataSchema rows.

    Args:
        table_names: Optional comma-separated, quoted table names to filter by.
            Format: "'table1', 'table2'". When None, all tables in the schemas are returned.
    """
    render_kwargs = dict(
        database_name=database,
        schemas=schemas,
        offset=0,
        limit=5000,
    )
    if table_names is not None:
        render_kwargs["table_names"] = table_names
    query = templates.render_template(
        templates.get_tables_query_template,
        **render_kwargs,
    )
    results = connector.execute_and_fetch_all(query)
    return [MetadataSchema(*row) for row in results]


def collect_test_table_columns(connector, templates, functional_ops) -> List[SchemaItem]:
    """Run the get_columns_query_template and return columns for the test table.

    The ``tables`` filter format varies by dialect — some WHERE clauses match
    on ``schema.table`` while the SELECT returns ``database.schema.table``.
    To handle this we pass every possible dotted combination of the table
    identifier parts so the IN clause matches regardless of format.
    """
    tv = table_vars(functional_ops)
    db, schema, table = tv["database"], tv["schema"], tv["table"]
    candidates = {
        f"{db}.{schema}.{table}",
        f"{schema}.{table}",
        table,
    }
    tables_param = ", ".join([f"'{c}'" for c in candidates])
    query = templates.render_template(
        templates.get_columns_query_template,
        tables=tables_param,
        database_name=db,
    )
    results = connector.execute_and_fetch_all(query)
    target = table.lower()
    columns = []
    for full_id, col_name, col_type in results:
        if target in full_id.lower():
            columns.append(SchemaItem(name=col_name, type=col_type))
    return columns


def find_test_table(metadata: List[MetadataSchema], functional_ops) -> Optional[MetadataSchema]:
    """Find the test table in metadata results (case-insensitive match)."""
    tv = table_vars(functional_ops)
    db = tv["database"].lower()
    schema = tv["schema"].lower()
    table = tv["table"].lower()
    for m in metadata:
        if (
            m.database_name.lower() == db
            and m.schema_name.lower() == schema
            and m.table_name.lower() == table
        ):
            return m
    return None


def schemas_param(functional_ops) -> str:
    """Build the schemas parameter the way get_tables_query_template expects."""
    return f"'{table_vars(functional_ops)['schema']}'"


def table_names_param(functional_ops) -> str:
    """Build the table_names parameter for filtering to just the test table."""
    return f"'{table_vars(functional_ops)['table']}'"


#############################################
# Fixtures
#############################################
@pytest.fixture(scope="module", autouse=True)
def functional_setup(connector, templates, functional_ops):
    """Clean up stale test tables before and after the test module."""
    if functional_ops is None:
        yield
        return
    # Pre-cleanup
    connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))
    yield
    # Post-cleanup
    connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))


def _skip_if_no_ops(functional_ops):
    if functional_ops is None:
        pytest.skip("FunctionalTestOperations not implemented for this connector")


#############################################
# Tests
#############################################
class TestTableDiscovery:
    def test_table_discovery_after_create(self, connector, templates, functional_ops):
        """New table appears in metadata after creation."""
        _skip_if_no_ops(functional_ops)

        tv = table_vars(functional_ops)
        schemas = schemas_param(functional_ops)

        # Ensure table does not exist
        connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))
        before = collect_metadata(connector, templates, tv["database"], schemas, table_names=table_names_param(functional_ops))
        assert find_test_table(before, functional_ops) is None, (
            f"Test table {tv['table']} already appears in metadata "
            f"before creation. Drop it manually or check your drop_test_table_template()."
        )

        # Create and verify
        connector.execute_only(render_functional(templates, templates.create_test_table_template, functional_ops))
        try:
            after = collect_metadata(connector, templates, tv["database"], schemas, table_names=table_names_param(functional_ops))
            found = find_test_table(after, functional_ops)
            assert found is not None, (
                f"Table {tv['table']} was not discovered after creation. "
                f"Your get_tables_query_template() may be filtering it out or using a stale cache."
            )
        finally:
            connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))

    def test_table_discovery_after_drop(self, connector, templates, functional_ops):
        """Dropped table disappears from metadata."""
        _skip_if_no_ops(functional_ops)

        tv = table_vars(functional_ops)
        schemas = schemas_param(functional_ops)

        # Create table and verify it appears
        connector.execute_only(render_functional(templates, templates.create_test_table_template, functional_ops))
        before = collect_metadata(connector, templates, tv["database"], schemas, table_names=table_names_param(functional_ops))
        assert find_test_table(before, functional_ops) is not None, (
            f"Table {tv['table']} was not found after creation. "
            f"Cannot test drop behavior."
        )

        # Drop and verify
        connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))
        after = collect_metadata(connector, templates, tv["database"], schemas, table_names=table_names_param(functional_ops))
        assert find_test_table(after, functional_ops) is None, (
            f"Table {tv['table']} still appears in metadata after being dropped. "
            f"Your get_tables_query_template() may be reading from a stale catalog or cache."
        )


class TestVolumeAndFreshness:
    def test_volume_change_after_insert(self, connector, templates, functional_ops):
        """row_count increases after inserting rows."""
        _skip_if_no_ops(functional_ops)

        tv = table_vars(functional_ops)
        schemas = schemas_param(functional_ops)

        connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))
        connector.execute_only(render_functional(templates, templates.create_test_table_template, functional_ops))
        try:
            before_metadata = collect_metadata(connector, templates, tv["database"], schemas, table_names=table_names_param(functional_ops))
            before_table = find_test_table(before_metadata, functional_ops)
            assert before_table is not None, (
                f"Test table {tv['table']} not found in metadata after creation."
            )

            if before_table.row_count is None:
                pytest.skip(
                    "row_count is None — your get_tables_query_template() does not return row counts. "
                    "Skipping volume change test."
                )

            before_count = before_table.row_count
            num_rows = 10
            connector.execute_only(render_functional(
                templates, templates.insert_rows_template, functional_ops, num_rows=num_rows,
            ))

            after_metadata = collect_metadata(connector, templates, tv["database"], schemas, table_names=table_names_param(functional_ops))
            after_table = find_test_table(after_metadata, functional_ops)
            assert after_table is not None, "Test table disappeared from metadata after insert."
            after_count = after_table.row_count

            assert after_count is not None and after_count > before_count, (
                f"row_count did not increase after inserting {num_rows} rows. "
                f"Before: {before_count}, After: {after_count}. "
                f"Your get_tables_query_template() may be reading from a statistics table "
                f"that only updates when stats are collected."
            )
        finally:
            connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))

    def test_byte_count_change_after_insert(self, connector, templates, functional_ops):
        """byte_count increases after inserting rows."""
        _skip_if_no_ops(functional_ops)

        tv = table_vars(functional_ops)
        schemas = schemas_param(functional_ops)

        connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))
        connector.execute_only(render_functional(templates, templates.create_test_table_template, functional_ops))
        try:
            before_metadata = collect_metadata(connector, templates, tv["database"], schemas, table_names=table_names_param(functional_ops))
            before_table = find_test_table(before_metadata, functional_ops)
            assert before_table is not None, (
                f"Test table {tv['table']} not found in metadata after creation."
            )

            if before_table.byte_count is None:
                pytest.skip(
                    "byte_count is None — your get_tables_query_template() does not return byte counts. "
                    "Skipping byte count volume change test."
                )

            before_bytes = before_table.byte_count
            num_rows = 10
            connector.execute_only(render_functional(
                templates, templates.insert_rows_template, functional_ops, num_rows=num_rows,
            ))

            after_metadata = collect_metadata(connector, templates, tv["database"], schemas, table_names=table_names_param(functional_ops))
            after_table = find_test_table(after_metadata, functional_ops)
            assert after_table is not None, "Test table disappeared from metadata after insert."
            after_bytes = after_table.byte_count

            assert after_bytes is not None and after_bytes > before_bytes, (
                f"byte_count did not increase after inserting {num_rows} rows. "
                f"Before: {before_bytes}, After: {after_bytes}. "
                f"Your get_tables_query_template() may be reading from a statistics table "
                f"that only updates when stats are collected."
            )
        finally:
            connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))

    def test_freshness_change_after_insert(self, connector, templates, functional_ops):
        """last_update_time advances after inserting rows."""
        _skip_if_no_ops(functional_ops)

        tv = table_vars(functional_ops)
        schemas = schemas_param(functional_ops)

        connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))
        connector.execute_only(render_functional(templates, templates.create_test_table_template, functional_ops))
        try:
            before_metadata = collect_metadata(connector, templates, tv["database"], schemas, table_names=table_names_param(functional_ops))
            before_table = find_test_table(before_metadata, functional_ops)
            assert before_table is not None, (
                f"Test table {tv['table']} not found in metadata after creation."
            )

            if before_table.last_update_time is None:
                pytest.skip(
                    "last_update_time is None — your get_tables_query_template() does not return "
                    "freshness data. Skipping freshness change test."
                )

            before_time = before_table.last_update_time

            # Small delay to ensure timestamp difference is detectable
            time.sleep(1)
            connector.execute_only(render_functional(
                templates, templates.insert_rows_template, functional_ops, num_rows=5,
            ))

            after_metadata = collect_metadata(connector, templates, tv["database"], schemas, table_names=table_names_param(functional_ops))
            after_table = find_test_table(after_metadata, functional_ops)
            assert after_table is not None, "Test table disappeared from metadata after insert."
            after_time = after_table.last_update_time

            assert after_time is not None and after_time > before_time, (
                f"last_update_time did not advance after inserting rows. "
                f"Before: {before_time}, After: {after_time}. "
                f"Your get_tables_query_template() may be reading from a statistics table "
                f"that only updates when stats are collected."
            )
        finally:
            connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))


class TestSchemaChange:
    def test_schema_change_after_add_column(self, connector, templates, functional_ops):
        """New column appears in column metadata after ALTER TABLE ADD COLUMN."""
        _skip_if_no_ops(functional_ops)

        if not templates.get_columns_query_template():
            pytest.skip("get_columns_query_template not implemented. Skipping schema change test.")

        connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))
        connector.execute_only(render_functional(templates, templates.create_test_table_template, functional_ops))
        try:
            before_cols = collect_test_table_columns(connector, templates, functional_ops)
            before_names = {c.name.lower() for c in before_cols}

            col_name = "pandora_test_col"
            connector.execute_only(render_functional(
                templates, templates.add_column_template, functional_ops,
                column_name=col_name, column_type="TEXT",
            ))

            after_cols = collect_test_table_columns(connector, templates, functional_ops)
            after_names = {c.name.lower() for c in after_cols}

            assert col_name.lower() in after_names, (
                f"Column '{col_name}' was not found in column metadata after ALTER TABLE ADD COLUMN. "
                f"Columns before: {sorted(before_names)}, Columns after: {sorted(after_names)}. "
                f"Your get_columns_query_template() may be reading from a stale catalog."
            )
        finally:
            connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))

    def test_schema_change_after_drop_column(self, connector, templates, functional_ops):
        """Dropped column disappears from column metadata."""
        _skip_if_no_ops(functional_ops)

        if not templates.get_columns_query_template():
            pytest.skip("get_columns_query_template not implemented.")

        if not getattr(templates, 'drop_column_template', None) or not templates.drop_column_template():
            pytest.skip("drop_column_template not implemented.")

        connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))
        connector.execute_only(render_functional(templates, templates.create_test_table_template, functional_ops))
        try:
            col_name = "pandora_drop_col"
            connector.execute_only(render_functional(
                templates, templates.add_column_template, functional_ops,
                column_name=col_name, column_type="TEXT",
            ))

            mid_cols = collect_test_table_columns(connector, templates, functional_ops)
            mid_names = {c.name.lower() for c in mid_cols}
            assert col_name.lower() in mid_names, (
                f"Column '{col_name}' was not found after ADD COLUMN — cannot test drop."
            )

            connector.execute_only(render_functional(
                templates, templates.drop_column_template, functional_ops,
                column_name=col_name,
            ))

            after_cols = collect_test_table_columns(connector, templates, functional_ops)
            after_names = {c.name.lower() for c in after_cols}

            assert col_name.lower() not in after_names, (
                f"Column '{col_name}' still appears in column metadata after DROP COLUMN. "
                f"Columns after: {sorted(after_names)}. "
                f"Your get_columns_query_template() may be reading from a stale catalog."
            )
        finally:
            connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))

class TestQueryLogCapture:
    def test_query_log_capture(self, connector, templates, functional_ops):
        """Executed query appears in query logs."""
        _skip_if_no_ops(functional_ops)

        if not templates.get_query_logs_query_template():
            pytest.skip("get_query_logs_query_template not implemented. Skipping query log test.")

        try:
            lineage_sql = render_functional(templates, templates.create_lineage_query_template, functional_ops)
        except (NotImplementedError, Exception):
            pytest.skip("create_lineage_query_template not implemented. Skipping query log test.")

        # Ensure the test table exists so the lineage query can run
        connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))
        connector.execute_only(render_functional(templates, templates.create_test_table_template, functional_ops))
        try:
            start_time = datetime.now(tz=UTC)
            connector.execute_only(lineage_sql)

            # Allow time for the query to appear in logs
            time.sleep(2)
            end_time = datetime.now(tz=UTC) + timedelta(minutes=5)

            query = templates.render_template(
                templates.get_query_logs_query_template,
                start_time=start_time,
                end_time=end_time,
                limit=1000,
                offset=0,
            )
            results = connector.execute_and_fetch_all(query)

            # Search for the lineage query text in the results.
            # Query log rows vary by dialect but the SQL text is typically in one of the columns.
            found = False
            lineage_lower = lineage_sql.lower().strip()
            for row in results:
                for col in row:
                    if isinstance(col, str) and lineage_lower in col.lower():
                        found = True
                        break
                if found:
                    break

            assert found, (
                f"The lineage query was not found in query logs. "
                f"Searched {len(results)} log entries between {start_time} and {end_time}. "
                f"Query executed: {lineage_sql!r}. "
                f"Your get_query_logs_query_template() may not capture this type of query."
            )
        finally:
            connector.execute_only(render_functional(templates, templates.drop_test_table_template, functional_ops))
