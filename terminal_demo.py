from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from support_reply_assistant.policies import load_policy_sections
from support_reply_assistant.schemas import TicketContext
from support_reply_assistant.workflows import generate_baseline_reply, generate_grounded_reply


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _load_cases() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "test_tickets.csv")


def _resolve_case(case_id: str) -> TicketContext:
    cases = _load_cases()
    match = cases.loc[cases["case_id"] == case_id]
    if match.empty:
        available = ", ".join(cases["case_id"].tolist())
        raise ValueError(f"Unknown case_id '{case_id}'. Available cases: {available}")

    row = match.iloc[0]
    return TicketContext(
        customer_ticket=row["customer_ticket"],
        account_tier=row["account_tier"],
        ownership_verified=bool(row["ownership_verified"]),
    )


def _print_block(title: str, payload: dict) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a terminal demo of the Policy-Grounded Support Reply Assistant."
    )
    parser.add_argument(
        "--case-id",
        default="refund_outside_01",
        help="Case ID from data/test_tickets.csv to run in the demo.",
    )
    args = parser.parse_args()

    context = _resolve_case(args.case_id)
    policy_sections = load_policy_sections(ROOT / "data" / "policy_handbook.md")

    print("Policy-Grounded Support Reply Assistant")
    print(f"Demo case: {args.case_id}")
    print("\nTicket context:")
    print(json.dumps(context.model_dump(), indent=2))

    try:
        baseline = generate_baseline_reply(context)
        grounded, retrieved = generate_grounded_reply(context, policy_sections)
    except Exception as exc:
        print(f"\nError: {exc}")
        print("Make sure .env contains a valid GOOGLE_API_KEY before running the demo.")
        raise SystemExit(1) from exc

    _print_block("Prompt-only baseline", baseline.model_dump())
    _print_block("Policy-grounded workflow", grounded.model_dump())

    print("\n=== Retrieved policy sections ===")
    for section in retrieved:
        print(f"- {section.policy_id}: {section.title}")


if __name__ == "__main__":
    main()
