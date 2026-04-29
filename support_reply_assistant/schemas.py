from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["low", "medium", "high"]
EscalationTarget = Literal["none", "billing", "security", "legal", "account"]
AccountTier = Literal["Free", "Pro", "Enterprise"]


class TicketContext(BaseModel):
    customer_ticket: str
    account_tier: AccountTier
    ownership_verified: bool


class SupportReply(BaseModel):
    draft_reply: str
    internal_notes: str
    risk_level: RiskLevel
    escalation_required: bool
    escalation_target: EscalationTarget
    cited_policy_ids: list[str] = Field(default_factory=list)
