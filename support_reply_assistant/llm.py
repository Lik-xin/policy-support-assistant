from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import requests


def get_api_key() -> str:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() == "your-key-here":
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env or export the key before running the app."
        )
    return api_key


def get_model_name() -> str:
    return os.getenv("GOOGLE_MODEL", "gemini-2.5-flash-lite")


def _response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "draft_reply": {"type": "string"},
            "internal_notes": {"type": "string"},
            "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
            "escalation_required": {"type": "boolean"},
            "escalation_target": {
                "type": "string",
                "enum": ["none", "billing", "security", "legal", "account"],
            },
            "cited_policy_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "draft_reply",
            "internal_notes",
            "risk_level",
            "escalation_required",
            "escalation_target",
            "cited_policy_ids",
        ],
        "propertyOrdering": [
            "draft_reply",
            "internal_notes",
            "risk_level",
            "escalation_required",
            "escalation_target",
            "cited_policy_ids",
        ],
    }


def _extract_text(response_json: dict[str, Any]) -> str:
    candidates = response_json.get("candidates", [])
    if not candidates:
        prompt_feedback = response_json.get("promptFeedback")
        raise RuntimeError(f"Gemini returned no candidates. Prompt feedback: {prompt_feedback}")

    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [part.get("text", "") for part in parts if "text" in part]
    if not text_parts:
        raise RuntimeError(f"Gemini returned no text parts: {response_json}")
    return "".join(text_parts)


def _retry_delay_seconds(response: requests.Response) -> int:
    try:
        payload = response.json()
    except Exception:
        payload = {}

    details = payload.get("error", {}).get("details", [])
    for detail in details:
        retry_delay = detail.get("retryDelay")
        if isinstance(retry_delay, str) and retry_delay.endswith("s"):
            try:
                return max(1, int(float(retry_delay[:-1])) + 1)
            except ValueError:
                pass

    match = re.search(r"Please retry in ([0-9]+(?:\.[0-9]+)?)s", response.text)
    if match:
        return max(1, int(float(match.group(1))) + 1)
    return 30


def generate_json(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> dict[str, Any]:
    api_key = get_api_key()
    model = get_model_name()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": system_prompt,
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": user_prompt,
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
            "responseSchema": _response_schema(),
        },
    }

    for attempt in range(8):
        response = requests.post(
            url,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        if response.status_code in {429, 503} and attempt < 7:
            time.sleep(_retry_delay_seconds(response))
            continue
        if response.status_code >= 400:
            raise RuntimeError(f"Gemini API error {response.status_code}: {response.text}")
        content = _extract_text(response.json()).strip() or "{}"
        return json.loads(content)

    raise RuntimeError("Gemini API rate-limit retry loop exhausted.")
