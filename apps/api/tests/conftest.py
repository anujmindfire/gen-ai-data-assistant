"""Pytest configuration and shared test fixtures."""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure root directory is on sys.path for monorepo imports
root_dir = Path(__file__).resolve().parents[3]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from apps.api.app.main import app


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a synchronous TestClient instance bound to the FastAPI app."""
    return TestClient(app)
