import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "principal-sdk"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "board-core"))

from agent_delegation_principal import DelegationInput, build_task_spec  # noqa: E402


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
    print(payload["task_id"])


if __name__ == "__main__":
    main()
