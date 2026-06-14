import unittest

from agent_delegation_board.lifecycle import (
    approve_task,
    claim_task,
    close_task,
    publish_task,
    request_review,
    start_execution,
    submit_result,
)


class MemoryStore:
    def __init__(self):
        self.identities = {}
        self.active = {}
        self.closed = {}
        self.events = []

    def get_identity(self, identity_id):
        return self.identities[identity_id]

    def create_active_task(self, task):
        if task["task_id"] in self.active:
            raise ValueError("task already exists")
        self.active[task["task_id"]] = dict(task)
        return task

    def load_task(self, task_id):
        if task_id in self.active:
            return dict(self.active[task_id])
        return dict(self.closed[task_id])

    def load_active_task(self, task_id):
        return dict(self.active[task_id])

    def save_active_task(self, task):
        self.active[task["task_id"]] = dict(task)
        return task

    def close_active_task(self, task):
        self.closed[task["task_id"]] = dict(task)
        del self.active[task["task_id"]]
        return task

    def append_event(self, task_id, event_type, actor_identity_id, payload=None):
        event = {
            "task_id": task_id,
            "type": event_type,
            "actor_identity_id": actor_identity_id,
            "payload": payload or {},
        }
        self.events.append(event)
        return event

    def task_ref(self, task_id):
        return f"memory://tasks/{task_id}"


class LifecycleTest(unittest.TestCase):
    def test_lifecycle_runs_without_filesystem_adapter(self):
        store = MemoryStore()
        store.identities = _identities()
        task = _task()

        publish_task(store, task, "principal-codex-pc")
        claim_task(store, task["task_id"], "contractor-duoduo")
        start_execution(store, task["task_id"], "contractor-duoduo")
        submit_result(
            store,
            task["task_id"],
            "contractor-duoduo",
            "results/task-memory.md",
            {"smoke": "passed"},
        )
        request_review(store, task["task_id"], "board-duoduo")
        approve_task(
            store,
            task["task_id"],
            "principal-codex-pc",
            "reviews/task-memory.md",
        )
        close_task(store, task["task_id"], "board-duoduo")

        self.assertNotIn(task["task_id"], store.active)
        self.assertEqual(store.closed[task["task_id"]]["status"], "closed")
        self.assertIn("task_closed", [event["type"] for event in store.events])


def _identities():
    return {
        "principal-codex-pc": {
            "identity_id": "principal-codex-pc",
            "agent_id": "agent-codex",
            "role_type": "principal",
            "permissions": [
                "publish_task",
                "review_task",
                "approve_task",
                "reject_task",
            ],
            "board_protocol_version": "1.0",
            "status": "active",
        },
        "contractor-duoduo": {
            "identity_id": "contractor-duoduo",
            "agent_id": "agent-duoduo",
            "role_type": "contractor",
            "permissions": ["claim_task", "start_execution", "submit_result"],
            "board_protocol_version": "1.0",
            "status": "active",
        },
        "board-duoduo": {
            "identity_id": "board-duoduo",
            "agent_id": "agent-duoduo",
            "role_type": "board",
            "permissions": [
                "append_event",
                "transition_status",
                "route_notification",
                "request_review",
                "close_task",
            ],
            "board_protocol_version": "1.0",
            "status": "active",
        },
    }


def _task():
    return {
        "task_id": "task-memory-001",
        "title": "Memory lifecycle task",
        "principal_identity_id": "principal-codex-pc",
        "contractor_identity_id": "contractor-duoduo",
        "board_identity_id": "board-duoduo",
        "status": "published",
        "board_protocol_version": "1.0",
    }


if __name__ == "__main__":
    unittest.main()
