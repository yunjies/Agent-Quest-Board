import argparse
import json
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "packages" / "board-core"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "principal-sdk"))
sys.path.insert(0, str(REPO_ROOT / "adapters" / "filesystem"))
sys.path.insert(0, str(REPO_ROOT / "apps" / "contractor" / "hermes-contractor"))
sys.path.insert(0, str(REPO_ROOT / "apps" / "board-interface" / "lark-topic-board"))

from agent_delegation_filesystem import (  # noqa: E402
    close_task,
    init_board,
    publish_task,
    register_agent,
    register_identity,
    request_review,
)
from agent_delegation_hermes_contractor import HermesContractor  # noqa: E402
from agent_delegation_lark_topic_board import LarkTopicBoard  # noqa: E402
from agent_delegation_principal import (  # noqa: E402
    DelegationInput,
    ReviewInput,
    build_review_payload,
    build_task_spec,
)


PRINCIPAL_ID = "principal-codex-pc"
CONTRACTOR_ID = "contractor-duoduo"
BOARD_ID = "board-duoduo"


def main():
    args = parse_args()
    board_root = Path(args.board_root).resolve()
    if args.clean:
        clean_board_root(board_root)

    init_board(board_root)
    register_runtime(board_root)

    topic_board = LarkTopicBoard(
        mapping_store=str(board_root / "frontends" / "lark-topic-map.json")
    )

    task = build_task()
    task_id = task["task_id"]
    print(f"[e2e] publish task: {task_id}")
    publish_task(board_root, task, PRINCIPAL_ID)
    sync_frontend(board_root, topic_board, task_id)

    contractor = HermesContractor(
        board_root,
        identity_id=CONTRACTOR_ID,
        results_dir=board_root / "artifacts" / task_id,
        logs_dir=board_root / "artifacts" / task_id,
    )
    contractor.ensure_registered()

    assigned = contractor.get_assigned_tasks()
    assert any(item["task_id"] == task_id for item in assigned), "contractor cannot see assigned task"

    print("[e2e] contractor claim/start/execute/submit")
    contractor.claim_task(task_id)
    contractor.start_execution(task_id)
    execution = contractor.execute_task(task_id)
    contractor.submit_result(
        task_id,
        result_file=execution["result_file"],
        artifacts=execution["artifacts"],
        execution_log=execution["execution_log"],
    )
    sync_frontend(board_root, topic_board, task_id)

    print("[e2e] board request review")
    request_review(board_root, task_id, BOARD_ID)
    sync_frontend(board_root, topic_board, task_id)

    print("[e2e] principal approve")
    review_file = write_review(board_root, task_id, execution)
    from agent_delegation_filesystem import approve_task

    approve_task(board_root, task_id, PRINCIPAL_ID, str(review_file.as_posix()))
    sync_frontend(board_root, topic_board, task_id)

    print("[e2e] board close task")
    close_task(board_root, task_id, BOARD_ID)
    sync_frontend(board_root, topic_board, task_id)

    verify_closed(board_root, topic_board, task_id, review_file, execution)
    write_observer_summary(board_root, topic_board, task_id)

    print("[e2e] PASS local end-to-end delegation flow")
    print(f"[e2e] board_root={board_root}")
    print(f"[e2e] task_id={task_id}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a local filesystem end-to-end Agent Delegation Board flow."
    )
    parser.add_argument(
        "--board-root",
        default=str(REPO_ROOT / ".local" / "e2e-board"),
        help="Filesystem board runtime root.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete the local board root before running. Only allowed under repo .local.",
    )
    return parser.parse_args()


def clean_board_root(board_root):
    local_root = (REPO_ROOT / ".local").resolve()
    try:
        board_root.relative_to(local_root)
    except ValueError as exc:
        raise SystemExit("--clean is only allowed for paths under repo .local") from exc
    if board_root.exists():
        shutil.rmtree(board_root)


def register_runtime(board_root):
    register_agent(
        board_root,
        {
            "agent_id": "agent-codex-local",
            "name": "Codex PC local principal",
            "implementation_version": "0.1.0",
            "board_protocol_version": "1.0",
        },
    )
    register_agent(
        board_root,
        {
            "agent_id": "agent-duoduo-local",
            "name": "Duoduo Hermes contractor",
            "implementation_version": "0.1.0",
            "board_protocol_version": "1.0",
        },
    )
    register_agent(
        board_root,
        {
            "agent_id": "agent-board-local",
            "name": "Filesystem board runtime",
            "implementation_version": "0.1.0",
            "board_protocol_version": "1.0",
        },
    )
    register_identity(
        board_root,
        {
            "identity_id": PRINCIPAL_ID,
            "agent_id": "agent-codex-local",
            "role_type": "principal",
            "permissions": [
                "publish_task",
                "review_task",
                "approve_task",
                "reject_task",
                "score_contractor",
            ],
            "board_protocol_version": "1.0",
            "implementation_version": "0.1.0",
            "status": "active",
        },
    )
    register_identity(
        board_root,
        {
            "identity_id": CONTRACTOR_ID,
            "agent_id": "agent-duoduo-local",
            "role_type": "contractor",
            "permissions": [
                "claim_task",
                "start_execution",
                "submit_result",
                "request_clarification",
                "mark_blocked",
                "revise_task",
                "resubmit_result",
            ],
            "board_protocol_version": "1.0",
            "implementation_version": "0.1.0",
            "status": "active",
        },
    )
    register_identity(
        board_root,
        {
            "identity_id": BOARD_ID,
            "agent_id": "agent-board-local",
            "role_type": "board",
            "permissions": [
                "append_event",
                "transition_status",
                "route_notification",
                "request_review",
                "close_task",
            ],
            "board_protocol_version": "1.0",
            "implementation_version": "0.1.0",
            "status": "active",
        },
    )


def build_task():
    description = (
        "Run a local end-to-end integration check for Agent Delegation Board. "
        "The contractor must claim the task, execute the deterministic skeleton, "
        "submit a result file and execution log, then wait for principal review. "
        "The board must keep filesystem task snapshots, event jsonl, artifacts, "
        "and frontend topic mapping consistent across the whole lifecycle."
    )
    return build_task_spec(
        DelegationInput(
            title="Local e2e delegation board smoke",
            description=description,
            principal_identity_id=PRINCIPAL_ID,
            contractor_identity_id=CONTRACTOR_ID,
            board_identity_id=BOARD_ID,
            task_kind="coding",
            context=[
                "Use filesystem board runtime as the source of truth.",
                "Use lark-topic-board only as a frontend interface skeleton.",
            ],
            acceptance_tests=[
                "Task reaches closed status only after approved.",
                "Events contain publish, submit, review, approve, and close.",
                "Result file, execution log, review file, and topic map exist.",
            ],
            constraints=[
                "Do not call LLM from board identity.",
                "Do not use real Lark credentials or personal IDs.",
            ],
        )
    )


def sync_frontend(board_root, topic_board, task_id):
    events = read_events(board_root, task_id)
    task = load_task_snapshot(board_root, task_id)
    notifications = topic_board.batch_process_events(events, tasks=[task] if task else [])
    for notification in notifications:
        if notification.get("needs_topic_creation") and not topic_board.get_topic_for_task(task_id):
            topic_board.assign_topic(task_id, f"example-topic-{task_id}")
        if notification.get("event_type") == "task_closed":
            topic_board.close_topic(task_id)
    write_json(
        board_root / "frontends" / f"{task_id}-notifications.json",
        {"task_id": task_id, "notifications": notifications},
    )
    return notifications


def write_review(board_root, task_id, execution):
    review = build_review_payload(
        ReviewInput(
            task_id=task_id,
            principal_identity_id=PRINCIPAL_ID,
            verdict="approved",
            summary="Local e2e result contains result file and execution log.",
            evidence=[execution["result_file"], execution["execution_log"]],
            contractor_rating=8,
            rating_breakdown={
                "result_file": 2,
                "execution_log": 2,
                "protocol_compliance": 2,
                "smoke_passed": 2,
            },
        )
    )
    review_file = board_root / "artifacts" / task_id / f"{task_id}-review.json"
    write_json(review_file, review)
    return review_file


def verify_closed(board_root, topic_board, task_id, review_file, execution):
    closed_task = board_root / "tasks" / "closed" / f"{task_id}.json"
    active_task = board_root / "tasks" / "active" / f"{task_id}.json"
    assert closed_task.exists(), "closed task snapshot missing"
    assert not active_task.exists(), "active task snapshot should be moved after close"

    task = json.loads(closed_task.read_text(encoding="utf-8"))
    assert task["status"] == "closed", f"unexpected final status: {task['status']}"
    assert task["review_verdict"] == "approved", "review verdict was not persisted"
    assert task["review_file"] == str(review_file.as_posix()), "review file path mismatch"
    assert Path(execution["result_file"]).exists(), "result file missing"
    assert Path(execution["execution_log"]).exists(), "execution log missing"

    event_types = [event["type"] for event in read_events(board_root, task_id)]
    for required in [
        "task_published",
        "result_submitted",
        "review_requested",
        "review_approved",
        "task_closed",
    ]:
        assert required in event_types, f"missing event: {required}"

    topic = topic_board.get_topic_for_task(task_id)
    assert topic and topic["status"] == "closed", "frontend topic was not closed"


def write_observer_summary(board_root, topic_board, task_id):
    task = json.loads(
        (board_root / "tasks" / "closed" / f"{task_id}.json").read_text(encoding="utf-8")
    )
    events = read_events(board_root, task_id)
    summary = {
        "task_id": task_id,
        "status": task["status"],
        "principal_identity_id": task["principal_identity_id"],
        "contractor_identity_id": task["contractor_identity_id"],
        "board_identity_id": task["board_identity_id"],
        "event_count": len(events),
        "event_types": [event["type"] for event in events],
        "topic": topic_board.get_topic_for_task(task_id),
        "closed_task": str((board_root / "tasks" / "closed" / f"{task_id}.json").as_posix()),
        "event_log": str((board_root / "events" / f"{task_id}.jsonl").as_posix()),
        "notifications": str(
            (board_root / "frontends" / f"{task_id}-notifications.json").as_posix()
        ),
    }
    write_json(board_root / "frontends" / f"{task_id}-observer-summary.json", summary)


def read_events(board_root, task_id):
    event_path = board_root / "events" / f"{task_id}.jsonl"
    if not event_path.exists():
        return []
    return [
        json.loads(line)
        for line in event_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_task_snapshot(board_root, task_id):
    for relative in ("tasks/active", "tasks/closed"):
        path = board_root / relative / f"{task_id}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
