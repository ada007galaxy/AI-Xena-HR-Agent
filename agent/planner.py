"""Intent planning for the HR agent.

OpenRouter is used when configured. A deterministic planner is retained as a
safe fallback for smoke tests and local development without an API key.
"""

from __future__ import annotations

import json
import re
from typing import Any

import requests

from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL

ALLOWED_TOOLS = {
    "search_policy_documents",
    "get_policy_section",
    "lookup_employee_profile",
    "check_pto_balance",
    "lookup_benefits_status",
    "check_policy_compliance",
    "create_mock_hr_ticket",
    "draft_hr_email",
}

SYSTEM = """You are the planning component of an HR policy agent.
Return ONLY valid JSON with this shape:
{
  "intent": "policy_qa|remote_work|pto|benefits|expense|case_triage|unknown",
  "employee_id": "EMP001 or null",
  "needs_clarification": false,
  "clarification_question": "",
  "tool_calls": [{"name": "tool", "arguments": {}}],
  "action": "none|draft_email|mock_ticket",
  "reason": "brief operational reason"
}

Rules:
- Use only the supplied tool names.
- Never expose chain-of-thought.
- Policy questions should use search_policy_documents.
- Employee-specific tasks should use lookup_employee_profile.
- PTO tasks should use check_pto_balance and policy retrieval.
- Benefits tasks should use lookup_benefits_status and policy retrieval.
- Remote work tasks should use employee lookup, policy retrieval and check_policy_compliance.
- A draft email is safe; a mock ticket is only allowed when the user explicitly asks for a ticket.
- If employee-specific information is required and no employee ID is present, ask for it unless a clearly named ID is present in the message.
"""


def _extract_employee_id(message: str) -> str | None:
    match = re.search(r"\bEMP\d{3}\b", message.upper())
    return match.group(0) if match else None


def deterministic_plan(message: str) -> dict[str, Any]:
    """Create a predictable plan without relying on an external model."""
    text = message.lower()
    employee_id = _extract_employee_id(message)

    if any(word in text for word in ["remote", "work from", "another state", "another country"]):
        if not employee_id:
            return {
                "intent": "remote_work",
                "employee_id": None,
                "needs_clarification": True,
                "clarification_question": "Please provide the employee ID, for example EMP001.",
                "tool_calls": [],
                "action": "none",
                "reason": "Remote-work eligibility is employee-specific.",
            }
        return {
            "intent": "remote_work",
            "employee_id": employee_id,
            "needs_clarification": False,
            "clarification_question": "",
            "tool_calls": [
                {"name": "lookup_employee_profile", "arguments": {"employee_id": employee_id}},
                {
                    "name": "search_policy_documents",
                    "arguments": {"query": "remote work location security tax approval six weeks", "k": 4},
                },
                {
                    "name": "check_policy_compliance",
                    "arguments": {
                        "policy_area": "remote work",
                        "employee_id": employee_id,
                        "details": message,
                    },
                },
            ],
            "action": "none",
            "reason": "Remote work requires employee context, policy evidence and a compliance review.",
        }

    if any(word in text for word in ["pto", "holiday", "annual leave", "days off", "time off"]):
        if not employee_id:
            return {
                "intent": "pto",
                "employee_id": None,
                "needs_clarification": True,
                "clarification_question": "Please provide the employee ID, for example EMP001.",
                "tool_calls": [],
                "action": "none",
                "reason": "PTO balance is employee-specific.",
            }
        calls = [
            {"name": "lookup_employee_profile", "arguments": {"employee_id": employee_id}},
            {"name": "check_pto_balance", "arguments": {"employee_id": employee_id}},
            {
                "name": "search_policy_documents",
                "arguments": {"query": "PTO annual leave request notice approval manager blackout periods", "k": 4},
            },
        ]
        if "draft" in text or "message" in text or "manager" in text:
            calls.append(
                {
                    "name": "draft_hr_email",
                    "arguments": {
                        "employee_id": employee_id,
                        "purpose": "PTO request",
                        "key_points": "I would like to request the PTO dates discussed. Please confirm manager approval and any scheduling requirements.",
                    },
                }
            )
        return {
            "intent": "pto",
            "employee_id": employee_id,
            "needs_clarification": False,
            "clarification_question": "",
            "tool_calls": calls,
            "action": "draft_email" if len(calls) == 4 else "none",
            "reason": "PTO guidance combines the employee balance, policy requirements and optional draft communication.",
        }

    if "ticket" in text and "create" in text:
        # Mock actions are allowed, but unsupported claims of approval must not be asserted.
        if "confirm" not in text:
            return {
                "intent": "case_triage",
                "employee_id": employee_id,
                "needs_clarification": True,
                "clarification_question": "I can create a clearly labelled mock HR ticket, but I cannot record an approval that is not supported by policy evidence. Please confirm that you want a mock ticket containing only the facts provided.",
                "tool_calls": [],
                "action": "mock_ticket",
                "reason": "Explicit confirmation is required before a mock operational action is created.",
            }
        return {
            "intent": "case_triage",
            "employee_id": employee_id,
            "needs_clarification": False,
            "clarification_question": "",
            "tool_calls": [{
                "name": "create_mock_hr_ticket",
                "arguments": {
                    "employee_id": employee_id or "UNKNOWN",
                    "subject": "HR request",
                    "summary": message,
                },
            }],
            "action": "mock_ticket",
            "reason": "The user explicitly confirmed a mock action.",
        }

    if "benefit" in text or "health insurance" in text or "pension" in text:
        if not employee_id:
            return {
                "intent": "benefits",
                "employee_id": None,
                "needs_clarification": True,
                "clarification_question": "Please provide the employee ID, for example EMP001.",
                "tool_calls": [],
                "action": "none",
                "reason": "Benefits status is employee-specific.",
            }
        return {
            "intent": "benefits",
            "employee_id": employee_id,
            "needs_clarification": False,
            "clarification_question": "",
            "tool_calls": [
                {"name": "lookup_employee_profile", "arguments": {"employee_id": employee_id}},
                {"name": "lookup_benefits_status", "arguments": {"employee_id": employee_id}},
                {"name": "search_policy_documents", "arguments": {"query": "benefits eligibility enrolment employment type", "k": 4}},
            ],
            "action": "none",
            "reason": "Benefits guidance needs eligibility policy and the employee's synthetic status.",
        }

    # General policy questions are handled by RAG only.
    return {
        "intent": "policy_qa",
        "employee_id": employee_id,
        "needs_clarification": False,
        "clarification_question": "",
        "tool_calls": [{"name": "search_policy_documents", "arguments": {"query": message, "k": 4}}],
        "action": "none",
        "reason": "The request appears to be a policy question that can be answered from the policy corpus.",
    }


def _call_openrouter(messages: list[dict[str, str]]) -> str:
    response = requests.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://xena-hr-agent.local",
            "X-Title": "Xena HR Agent",
        },
        json={"model": OPENROUTER_MODEL, "messages": messages, "temperature": 0},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def plan(message: str) -> dict[str, Any]:
    """Ask the LLM for a plan, validate it, and fall back safely if needed."""
    if not OPENROUTER_API_KEY:
        return deterministic_plan(message)

    try:
        raw = _call_openrouter([{"role": "system", "content": SYSTEM}, {"role": "user", "content": message}])
        candidate = json.loads(raw)
        calls = []

        for call in candidate.get("tool_calls", []):
            name = call.get("name")
            arguments = call.get("arguments", {})

            if name not in ALLOWED_TOOLS:
                continue

            # Normalize LLM-generated arguments to the MCP tool schemas.
            if name == "search_policy_documents":
                calls.append(
                    {
                        "name": name,
                        "arguments": {
                            "query": arguments.get("query")
                            or arguments.get("topic")
                            or message,
                            "k": arguments.get("k", 4),
                        },
                    }
                )

            elif name == "check_policy_compliance":
                calls.append(
                    {
                        "name": name,
                        "arguments": {
                            "policy_area": arguments.get("policy_area", "remote work"),
                            "employee_id": arguments.get("employee_id") or candidate.get("employee_id"),
                            "details": arguments.get("details") or message,
                        },
                    }
                )

            else:
                calls.append(
                    {
                        "name": name,
                        "arguments": arguments,
                    }
                )

        candidate["tool_calls"] = calls
        candidate["employee_id"] = candidate.get("employee_id") or _extract_employee_id(message)
        return candidate
    except Exception:
        # A failed planner must not prevent the application from answering safely.
        return deterministic_plan(message)
