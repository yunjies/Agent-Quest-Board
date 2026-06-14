import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "principal-sdk"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "board-core"))
sys.path.insert(0, str(REPO_ROOT / "adapters" / "filesystem"))

from agent_delegation_principal import (  # noqa: E402
    DelegationInput,
    ReviewInput,
    build_review_payload,
    build_task_spec,
)
from agent_delegation_filesystem import (  # noqa: E402
    approve_task,
    publish_task,
    register_identity,
    reject_task,
)


def main():
    if len(sys.argv) > 1 and sys.argv[1] not in {"publish", "review", "-h", "--help"}:
        legacy_args = _legacy_publish_args()
        print(publish(legacy_args))
        return

    parser = argparse.ArgumentParser(
        description="Codex Principal adapter for Agent Delegation Board."
    )
    subparsers = parser.add_subparsers(dest="command")

    publish_parser = subparsers.add_parser("publish", help="Build and publish a task.")
    _add_publish_args(publish_parser)

    review_parser = subparsers.add_parser("review", help="Write and submit a review.")
    _add_review_args(review_parser)

    args = parser.parse_args()
    if args.command == "publish":
        task_id = publish(args)
    elif args.command == "review":
        task_id = review(args)
    else:
        parser.print_help()
        raise SystemExit(2)
    print(task_id)


def publish(args):
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
            register_example_identities(
                args.board_root,
                args.principal_id,
                args.contractor_id,
                args.board_id,
            )
        publish_task(args.board_root, payload, args.principal_id)
    return payload["task_id"]


def review(args):
    payload = build_review_payload(
        ReviewInput(
            task_id=args.task_id,
            principal_identity_id=args.principal_id,
            verdict=args.verdict,
            summary=args.summary,
            evidence=args.evidence,
            revision_request=args.revision_request,
            contractor_rating=args.contractor_rating,
            rating_breakdown=_load_json_object(args.rating_breakdown_file),
        )
    )
    review_path = Path(args.review_file)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.board_root:
        if args.verdict == "approved":
            approve_task(
                args.board_root,
                args.task_id,
                args.principal_id,
                str(review_path.as_posix()),
            )
        else:
            reject_task(
                args.board_root,
                args.task_id,
                args.principal_id,
                str(review_path.as_posix()),
                args.revision_request,
            )
    return args.task_id


def register_example_identities(board_root, principal_id, contractor_id, board_id):
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


def _add_publish_args(parser):
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


def _add_review_args(parser):
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--principal-id", required=True)
    parser.add_argument("--verdict", choices=["approved", "rejected"], required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--revision-request")
    parser.add_argument("--contractor-rating", type=int)
    parser.add_argument("--rating-breakdown-file")
    parser.add_argument("--review-file", required=True)
    parser.add_argument("--board-root")


def _legacy_publish_args():
    legacy = argparse.ArgumentParser(
        description="Build a Principal task payload for Agent Delegation Board."
    )
    _add_publish_args(legacy)
    return legacy.parse_args()


def _load_json_object(path):
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("rating_breakdown_file must contain a JSON object")
    return data


if __name__ == "__main__":
    main()
