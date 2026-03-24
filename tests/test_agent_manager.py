import pytest
from unittest.mock import Mock, MagicMock
import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "1234567890:AAtesttoken")
os.environ.setdefault("ALLOWED_USER_ID", "12345678")
os.environ.setdefault("CLI_RUNNER", "generic")
os.environ.setdefault("CLI_COMMAND", "echo")

from agent_manager import get_running_instance, _agent_instance_map

@pytest.fixture(autouse=True)
def clean_map():
    _agent_instance_map.clear()
    yield
    _agent_instance_map.clear()

def test_get_running_instance_in_map_and_exists():
    mock_instances = Mock()
    mock_inst = MagicMock()
    mock_inst.agent_id = "agent_1"

    _agent_instance_map["agent_1"] = 123
    mock_instances.get.return_value = mock_inst

    result = get_running_instance("agent_1", mock_instances)

    assert result is mock_inst
    mock_instances.get.assert_called_once_with(123)
    mock_instances.list_all.assert_not_called()

def test_get_running_instance_in_map_but_removed():
    mock_instances = Mock()
    mock_instances.get.return_value = None

    mock_inst_other = MagicMock()
    mock_inst_other.agent_id = "agent_other"
    mock_instances.list_all.return_value = [mock_inst_other]

    _agent_instance_map["agent_2"] = 999

    result = get_running_instance("agent_2", mock_instances)

    assert result is None
    assert "agent_2" not in _agent_instance_map
    mock_instances.get.assert_called_once_with(999)
    mock_instances.list_all.assert_called_once()

def test_get_running_instance_fallback_scan():
    mock_instances = Mock()

    mock_inst = MagicMock()
    mock_inst.agent_id = "agent_3"
    mock_inst.id = 456

    mock_instances.list_all.return_value = [mock_inst]

    assert "agent_3" not in _agent_instance_map

    result = get_running_instance("agent_3", mock_instances)

    assert result is mock_inst
    assert _agent_instance_map["agent_3"] == 456
    mock_instances.get.assert_not_called()
    mock_instances.list_all.assert_called_once()

def test_get_running_instance_not_found():
    mock_instances = Mock()

    mock_inst = MagicMock()
    mock_inst.agent_id = "agent_other"

    mock_instances.list_all.return_value = [mock_inst]

    result = get_running_instance("agent_4", mock_instances)

    assert result is None
    mock_instances.get.assert_not_called()
    mock_instances.list_all.assert_called_once()

def test_get_running_instance_has_no_agent_id_attribute():
    mock_instances = Mock()

    mock_inst_other = MagicMock()
    # Mock missing attribute by making getattr raise AttributeError for agent_id
    type(mock_inst_other).agent_id = set() # some invalid type
    del type(mock_inst_other).agent_id # Now it misses agent_id

    # Actually wait we can just use simple classes

    class FakeInstanceWithoutAgentId:
        pass

    class FakeInstanceWithAgentId:
        def __init__(self, agent_id, id_val):
            self.agent_id = agent_id
            self.id = id_val

    inst1 = FakeInstanceWithoutAgentId()
    inst2 = FakeInstanceWithAgentId("agent_5", 555)

    mock_instances.list_all.return_value = [inst1, inst2]

    result = get_running_instance("agent_5", mock_instances)

    assert result is inst2
    assert _agent_instance_map["agent_5"] == 555
    mock_instances.get.assert_not_called()
    mock_instances.list_all.assert_called_once()
