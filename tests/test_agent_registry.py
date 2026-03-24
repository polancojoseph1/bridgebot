import os
import sqlite3
import pytest

# Need to setup env before importing anything
os.environ["TELEGRAM_BOT_TOKEN"] = "1234567890:AAtesttoken"
os.environ["ALLOWED_USER_ID"] = "12345678"
os.environ["CLI_RUNNER"] = "generic"

import agent_registry

# Fixture to mock the database to an in-memory SQLite database
@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    # Use an in-memory database for tests
    monkeypatch.setattr(agent_registry, "AGENTS_DB", ":memory:")

    # We also need to clear out any cached connection or state if there were any,
    # but _get_conn opens a new connection each time. However, :memory: is unique
    # per connection! So we need a shared memory database or to mock _get_conn
    # to return the same connection.
    # Actually, SQLite supports shared in-memory databases with URIs.
    # Let's use a URI memory database so all connections in the test share it.
    monkeypatch.setattr(agent_registry, "AGENTS_DB", "file:memdb1?mode=memory&cache=shared")

    # Force _get_conn to use uri=True
    orig_connect = sqlite3.connect
    def mock_connect(database, **kwargs):
        if database.startswith("file:memdb"):
            kwargs["uri"] = True
        return orig_connect(database, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", mock_connect)

    yield

    # After the test, all connections to this shared memory db will close, and it will be destroyed.


def test_delete_agent():
    """Test deleting an agent successfully and failing when agent does not exist."""
    # Setup: Create an agent
    agent_id = "test_agent_1"
    created = agent_registry.create_agent(
        agent_id=agent_id,
        name="Test Agent",
        agent_type="custom",
        system_prompt="You are a test agent."
    )
    assert created.id == agent_id

    # Verify agent exists
    assert agent_registry.get_agent(agent_id) is not None

    # Action: Delete the agent
    result = agent_registry.delete_agent(agent_id)

    # Assertion: Should return True
    assert result is True

    # Assertion: Agent should no longer exist
    assert agent_registry.get_agent(agent_id) is None

    # Action: Delete the same agent again
    result_second = agent_registry.delete_agent(agent_id)

    # Assertion: Should return False since it's already deleted
    assert result_second is False

    # Action/Assertion: Delete a completely non-existent agent
    assert agent_registry.delete_agent("non_existent_agent") is False
