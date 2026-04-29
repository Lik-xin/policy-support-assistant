from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


TOKEN_RE = re.compile(r"[a-z0-9_]+")
SECTION_RE = re.compile(r"^##\s+([A-Z0-9_]+)\s+-\s+(.+)$", re.MULTILINE)
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "have",
    "i",
    "if",
    "in",
    "is",
    "it",
    "last",
    "may",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "please",
    "that",
    "the",
    "their",
    "them",
    "there",
    "they",
    "this",
    "to",
    "us",
    "was",
    "we",
    "with",
    "you",
    "your",
}

POLICY_KEYWORDS = {
    "INVOICE_01": {
        "invoice",
        "receipt",
        "billing",
        "expense",
        "renewal",
    },
    "REFUND_01": {
        "refund",
        "renewal",
        "charged",
        "charge",
        "cancel",
        "usage",
    },
    "REFUND_02": {
        "refund",
        "renewal",
        "charged",
        "charge",
        "cancel",
        "usage",
        "used",
        "heavily",
        "outside",
        "weeks",
        "full",
        "yesterday",
    },
    "OWNERSHIP_01": {
        "owner",
        "ownership",
        "verified",
        "verification",
        "billing",
        "contact",
        "change",
        "downgrade",
        "upgrade",
    },
    "SECURITY_01": {
        "security",
        "login",
        "compromise",
        "compromised",
        "unauthorized",
        "mfa",
        "suspicious",
        "access",
    },
    "LEGAL_01": {
        "legal",
        "liability",
        "counsel",
        "litigation",
        "lawsuit",
        "indemnity",
        "binding",
    },
    "DATA_EXPORT_01": {
        "export",
        "data",
        "download",
        "quarter",
    },
}


def normalize_tokens(text: str) -> set[str]:
    return {token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS}


@dataclass
class PolicySection:
    policy_id: str
    title: str
    body: str

    @property
    def full_text(self) -> str:
        return f"{self.policy_id} - {self.title}\n{self.body.strip()}"

    @property
    def tokens(self) -> set[str]:
        return normalize_tokens(self.full_text)

    @property
    def title_tokens(self) -> set[str]:
        return normalize_tokens(self.title)


def load_policy_sections(path: str | Path) -> list[PolicySection]:
    text = Path(path).read_text(encoding="utf-8")
    matches = list(SECTION_RE.finditer(text))
    sections: list[PolicySection] = []

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.append(
            PolicySection(
                policy_id=match.group(1).strip(),
                title=match.group(2).strip(),
                body=body,
            )
        )

    return sections


def retrieve_policy_sections(query: str, sections: list[PolicySection], top_k: int = 3) -> list[PolicySection]:
    query_tokens = normalize_tokens(query)
    scored: list[tuple[int, int, int, PolicySection]] = []

    for section in sections:
        overlap = len(query_tokens & section.tokens)
        title_overlap = len(query_tokens & section.title_tokens)
        keyword_overlap = len(query_tokens & POLICY_KEYWORDS.get(section.policy_id, set()))
        scored.append((keyword_overlap, title_overlap, overlap, section))

    scored.sort(key=lambda item: (item[0], item[1], item[2], item[3].policy_id), reverse=True)
    filtered = [
        section
        for keyword_score, title_score, score, section in scored
        if keyword_score > 0 or title_score > 0 or score > 0
    ]
    return filtered[:top_k] if filtered else sections[:top_k]
