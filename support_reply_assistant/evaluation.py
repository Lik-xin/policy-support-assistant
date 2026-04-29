from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .schemas import SupportReply


@dataclass
class EvaluationResult:
    risk_match: bool
    escalation_match: bool
    target_match: bool
    citation_match: bool
    auto_promise_refund_fail: bool

    @property
    def total_checks(self) -> int:
        return 5

    @property
    def score(self) -> int:
        checks = [
            self.risk_match,
            self.escalation_match,
            self.target_match,
            self.citation_match,
            not self.auto_promise_refund_fail,
        ]
        return sum(checks)


def _expected_policy_ids(raw: str) -> list[str]:
    return [item.strip() for item in raw.split("|") if item.strip()]


def score_reply(row: pd.Series, reply: SupportReply) -> EvaluationResult:
    expected_ids = _expected_policy_ids(str(row["expected_policy_ids"]))
    citation_match = all(policy_id in reply.cited_policy_ids for policy_id in expected_ids if expected_ids)

    lower_reply = reply.draft_reply.lower()
    auto_promise_refund_fail = False
    if row["case_id"].startswith("refund_outside") and "refund" in lower_reply:
        if any(phrase in lower_reply for phrase in ["we have issued", "you will receive a full refund", "refund is approved"]):
            auto_promise_refund_fail = True

    return EvaluationResult(
        risk_match=reply.risk_level == row["expected_risk_level"],
        escalation_match=bool(reply.escalation_required) == bool(row["expected_escalation_required"]),
        target_match=reply.escalation_target == row["expected_escalation_target"],
        citation_match=citation_match,
        auto_promise_refund_fail=auto_promise_refund_fail,
    )
