import json

import pytest

pytestmark = [pytest.mark.connection]


def test_create_connection(connector):
    """Test that a database connection can be established."""
    assert connector.connection is not None, "Failed to create a connection to the database."


def test_create_cursor(connector):
    """Test that a cursor can be created from the connection."""
    assert connector.cursor is not None, "Failed to create a cursor from the connection."


def test_fetch_results_are_json_serializable(connector):
    """Verify fetch_all_results returns rows that can be JSON-serialized.

    The agent framework serializes query results to JSON for transport.
    Drivers that return custom row objects (e.g. pyodbc.Row) instead of
    plain tuples will break in production even though other tests pass,
    because those tests only index into rows without serializing them.
    """
    rows = connector.execute_and_fetch_all("SELECT 1 AS test_col")
    assert len(rows) > 0, "Expected at least one row from SELECT 1"

    try:
        json.dumps(rows)
    except TypeError as e:
        pytest.fail(
            f"fetch_all_results() returned rows that are not JSON-serializable: {e}. "
            f"Row type: {type(rows[0]).__name__}. "
            f"Ensure rows are converted to tuples or lists (e.g. [tuple(r) for r in cursor.fetchall()])."
        )


def test_cursor_description_is_json_serializable(connector):
    """Verify cursor.description is JSON-serializable after executing a query.

    The agent framework reads cursor.description to get column metadata and
    serializes it for transport. Some drivers (e.g. pyodbc) include Python
    type objects like <class 'str'> in the type_code field, which are not
    JSON-serializable. Wrap the cursor to convert these to strings.
    """
    connector.execute_and_fetch_all("SELECT 1 AS test_col")
    desc = connector.cursor.description
    assert desc is not None, "cursor.description should not be None after a query"

    try:
        json.dumps(desc)
    except TypeError as e:
        pytest.fail(
            f"cursor.description is not JSON-serializable: {e}. "
            f"If the driver includes Python type objects in description (e.g. pyodbc), "
            f"wrap the cursor to convert type_code to a string name."
        )
