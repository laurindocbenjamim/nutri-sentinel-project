"""
pytest configuration and shared fixtures for SMARTurinalysis.
"""

import pytest
from fastapi.testclient import TestClient

@pytest.fixture(autouse=True)
def establish_session(request):
    """
    Autouse fixture to establish a valid HttpOnly session cookie on the TestClient.
    Runs before each test to guarantee session validation middleware is satisfied.
    """
    module = request.module
    if module and hasattr(module, "client"):
        client = getattr(module, "client")
        if isinstance(client, TestClient):
            client.get("/")
