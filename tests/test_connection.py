import pytest

pytestmark = [pytest.mark.connection]


def test_create_connection(integration):
    """Test that a database connection can be established."""
    assert integration.connection is not None, "Failed to create a connection to the database."


def test_create_cursor(integration):
    """Test that a cursor can be created from the connection."""
    assert integration.cursor is not None, "Failed to create a cursor from the connection."
