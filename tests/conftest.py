import pytest

from tests.test_base import TestIntegration


@pytest.fixture(scope="session")
def integration():
    integration = TestIntegration()
    yield integration
    integration.close_connection()