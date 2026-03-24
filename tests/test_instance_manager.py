import asyncio
import pytest
from unittest.mock import MagicMock
from instance_manager import InstanceManager, Instance

@pytest.fixture
def manager():
    return InstanceManager()

def test_manager_initialization(manager):
    assert manager.count == 1
    assert manager.active.title == "Default"
    assert manager.active.id == 1

def test_remove_nonexistent_instance(manager):
    assert manager.remove(999) is None

def test_remove_wrong_owner(manager):
    inst = manager.create("Other", owner_id=1)
    # Try to remove it using owner_id=0
    assert manager.remove(inst.id, owner_id=0) is None
    # Still exists
    assert manager.get(inst.id) is not None

def test_remove_last_instance(manager):
    # manager starts with 1 instance for owner_id=0
    assert len(manager.list_all(for_owner_id=0)) == 1
    assert manager.remove(1, owner_id=0) is None
    # Still exists
    assert manager.get(1) is not None

def test_remove_non_active_instance(manager):
    inst = manager.create("Second", owner_id=0) # Now active is 2
    assert manager.count == 2
    assert manager.active_id == 2

    # Remove the non-active one (id=1)
    removed = manager.remove(1, owner_id=0)
    assert removed is not None
    assert removed.id == 1
    assert manager.count == 1
    assert manager.active_id == 2 # active id shouldn't change

def test_remove_active_global_instance(manager):
    inst1 = manager.get(1)
    inst2 = manager.create("Second", owner_id=0) # active becomes 2

    # Remove active
    removed = manager.remove(2, owner_id=0)
    assert removed is not None
    assert removed.id == 2
    assert manager.count == 1
    # active should be set to remaining inst1
    assert manager.active_id == 1

def test_remove_active_user_instance(manager):
    inst1 = manager.create("User1", owner_id=1)
    inst2 = manager.create("User2", owner_id=1) # active for user 1 is now inst2.id

    assert manager._user_active[1] == inst2.id

    removed = manager.remove(inst2.id, owner_id=1)
    assert removed is not None
    assert removed.id == inst2.id

    # user 1 active should be set to inst1.id
    assert manager._user_active[1] == inst1.id

def test_remove_last_user_instance_not_allowed(manager):
    inst = manager.create("User", owner_id=1)
    assert manager.remove(inst.id, owner_id=1) is None
    assert manager.get(inst.id) is not None

def test_remove_cancels_tasks(manager):
    inst = manager.create("Second", owner_id=0)

    worker_task = MagicMock()
    worker_task.done.return_value = False
    inst.worker_task = worker_task

    current_task = MagicMock()
    current_task.done.return_value = False
    inst.current_task = current_task

    removed = manager.remove(inst.id, owner_id=0)
    assert removed is not None

    worker_task.cancel.assert_called_once()
    current_task.cancel.assert_called_once()

def test_remove_does_not_cancel_completed_tasks(manager):
    inst = manager.create("Second", owner_id=0)

    worker_task = MagicMock()
    worker_task.done.return_value = True
    inst.worker_task = worker_task

    current_task = MagicMock()
    current_task.done.return_value = True
    inst.current_task = current_task

    removed = manager.remove(inst.id, owner_id=0)
    assert removed is not None

    worker_task.cancel.assert_not_called()
    current_task.cancel.assert_not_called()
