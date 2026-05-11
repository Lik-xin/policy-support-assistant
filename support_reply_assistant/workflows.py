from __future__ import annotations

from pathlib import Path

from .llm import generate_json
from .policies import PolicySection, retrieve_policy_sections
from .schemas import SupportReply, TicketContext


ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "prompts"


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _context_block(context: TicketContext) -> str:
    return "\n".join(
        [
            f"Customer ticket: {context.customer_ticket}",
            f"Account tier: {context.account_tier}",
            f"Ownership verified: {context.ownership_verified}",
        ]
    )


def _grounded_policy_block(sections: list[PolicySection]) -> str:
    chunks = []
    for section in sections:
        chunks.append(section.full_text)
    return "\n\n".join(chunks)


def _sanitize_baseline_reply(reply: SupportReply) -> SupportReply:
    updates = {"cited_policy_ids": []}
    if not reply.escalation_required:
        updates["escalation_target"] = "none"
    return reply.model_copy(update=updates)


def _sanitize_grounded_reply(reply: SupportReply, retrieved: list[PolicySection]) -> SupportReply:
    allowed_ids = {section.policy_id for section in retrieved}
    filtered_ids = [policy_id for policy_id in reply.cited_policy_ids if policy_id in allowed_ids]
    updates = {"cited_policy_ids": filtered_ids}
    if not reply.escalation_required:
        updates["escalation_target"] = "none"
    return reply.model_copy(update=updates)


def generate_baseline_reply(context: TicketContext) -> SupportReply:
    system_prompt = _load_prompt("baseline_system.txt")
    user_prompt = "\n\n".join(
        [
            "Use the ticket and account context below to draft a first-response support recommendation.",
            _context_block(context),
            (
                "Return JSON only. Since this is baseline mode, you do not have handbook excerpts. "
                "Leave cited_policy_ids empty unless you have a very strong reason not to."
            ),
        ]
    )
    raw = generate_json(system_prompt, user_prompt)
    reply = SupportReply.model_validate(raw)
    return _sanitize_baseline_reply(reply)


def generate_grounded_reply(
    context: TicketContext, sections: list[PolicySection], top_k: int = 3
) -> tuple[SupportReply, list[PolicySection]]:
    retrieval_query = "\n".join(
        [
            context.customer_ticket,
            f"account tier {context.account_tier}",
            f"ownership verified {context.ownership_verified}",
        ]
    )
    retrieved = retrieve_policy_sections(retrieval_query, sections, top_k=top_k)
    system_prompt = _load_prompt("grounded_system.txt")
    user_prompt = "\n\n".join(
        [
            "Use the ticket, account context, and policy packet below to draft a first-response support recommendation.",
            _context_block(context),
            "Retrieved policy packet:",
            _grounded_policy_block(retrieved),
            (
                "Return JSON only. Only cite policy IDs that appear in the retrieved policy packet. "
                "If the case is outside policy or risky, do not promise an outcome."
            ),
        ]
    )
    raw = generate_json(system_prompt, user_prompt)
    reply = SupportReply.model_validate(raw)
    reply = _sanitize_grounded_reply(reply, retrieved)
    return reply, retrieved
