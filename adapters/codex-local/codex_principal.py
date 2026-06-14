import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "principal-sdk"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "board-core"))
sys.path.insert(0, str(REPO_ROOT / "adapters" / "filesystem"))

from agent_delegation_principal import DelegationInput, build_task_spec  # noqa: E402
from agent_delegation_filesystem import publish_task, register_identity  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Build a Principal task payload for Agent Delegation Board."
    )
    parser.add_argument("--title", required=True)
    parser.add_argument("--description-file", required=True)
    parser.add_argument("--principal-id", required=True)
    parser.add_argument("--contractor-id", required=True)
    parser.add_argument("--board-id", default="board-unassigned")
    parser.add_argument("--task-kind", default="coding")
    parser.add_argument("--context", action="append", default=[])
    parser.add_argument("--acceptance-test", action="append", default=[])
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--board-root",
        help="Optional filesystem board root. When set, publish the generated task.",
    )
    parser.add_argument(
        "--register-example-identities",
        action="store_true",
        help="Register example v1 identities before publishing. For local smoke only.",
    )
    args = parser.parse_args()

    description = Path(args.description_file).read_text(encoding="utf-8")
    payload = build_task_spec(
        DelegationInput(
            title=args.title,
            description=description,
            principal_identity_id=args.principal_id,
            contractor_identity_id=args.contractor_id,
            board_identity_id=args.board_id,
            task_kind=args.task_kind,
            context=args.context,
            acceptance_tests=args.acceptance_test,
            constraints=args.constraint,
        )
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.board_root:
        if args.register_example_identities:
            _register_example_identities(
                args.board_root,
                args.principal_id,
                args.contractor_id,
                args.board_id,
            )
        publish_task(args.board_root, payload, args.principal_id)
    print(payload["task_id"])


def _register_example_identities(board_root, principal_id, contractor_id, board_id):
    register_identity(
        board_root,
        {
            "identity_id": principal_id,
            "agent_id": "agent-codex-local",
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
    )
    register_identity(
        board_root,
        {
            "identity_id": contractor_id,
            "agent_id": "agent-contractor-local",
            "role_type": "contractor",
            "permissions": ["claim_task", "start_execution", "submit_result"],
            "board_protocol_version": "1.0",
            "status": "active",
        },
    )
    register_identity(
        board_root,
        {
            "identity_id": board_id,
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
            "status": "active",
        },
    )


if __name__ == "__main__":
    main()
