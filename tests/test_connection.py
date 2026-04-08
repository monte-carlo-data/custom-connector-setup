import pytest

pytestmark = [pytest.mark.connection]


def test_create_connection(connector):
    """Test that a database connection can be established."""
    assert connector.connection is not None, "Failed to create a connection to the database."


def test_create_cursor(connector):
    """Test that a cursor can be created from the connection."""
    assert connector.cursor is not None, "Failed to create a cursor from the connection."
