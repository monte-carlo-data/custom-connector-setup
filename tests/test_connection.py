import pytest

pytestmark = [pytest.mark.connection]


def test_create_connection(integration):
    """Test that a database connection can be established."""
    assert integration.connection is not None, "Failed to create a connection to the database."


def test_create_cursor(integration):
    """Test that a cursor can be created from the connection."""
    assert integration.cursor is not None, "Failed to create a cursor from the connection."


def test_execute_simple_query(integration):
    """Test that a simple query can be executed and returns results."""
    results = integration.execute_and_fetch_all("SELECT 1")
    assert len(results) > 0, "Simple query returned no results."
    assert results[0][0] == 1
