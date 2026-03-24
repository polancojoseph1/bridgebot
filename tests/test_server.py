import pytest
from fastapi.testclient import TestClient

import os

# Set required environment variables for the app to initialize correctly
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "1234567890:AAtesttoken")
os.environ.setdefault("ALLOWED_USER_ID", "12345678")
os.environ.setdefault("CLI_RUNNER", "generic")
os.environ.setdefault("CLI_COMMAND", "echo")
os.environ.setdefault("ENV_FILE", "/dev/null")

from server import app
import health

client = TestClient(app)

def test_health_endpoint():
    """Test that the /health endpoint returns the expected structure and status code."""
    # Reset health stats for deterministic testing
    health._start_time = 0.0
    health._message_count = 0
    health._last_message_time = None
    health.init()

    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert data["message_count"] == 0
    assert data["last_message_time"] is None

def test_health_endpoint_after_message():
    """Test the /health endpoint after a message has been processed."""
    health.record_message()

    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert data["message_count"] == 1
    assert data["last_message_time"] is not None
