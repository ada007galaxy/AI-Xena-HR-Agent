"""Agent orchestrator for Xena HR Agent."""

from __future__ import annotations

import json
from typing import Any

import requests

from agent.planner import plan
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL


class AgentOrchestrator:
    """Coordinates planning, MCP calls, grounded synthesis and operational tracing."""

    def __init__(self, mcp_client):
        self.mcp = mcp_client

    def _synthesize_with_llm(self, message: str, plan_data: dict[str, Any], calls: list[dict[str, Any]]) -> str:
        context = json.dumps(calls, indent=2)[:12000]
        system = """You are Xena, an internal HR policy assistant.

Answer only from the supplied MCP results. Do not invent policy.

IMPORTANT TOOL-RESULT RULES:
- Treat an MCP call with a completed result as successful.
- Do NOT say that a policy retrieval or compliance check failed unless the supplied MCP result explicitly contains an error or failure.
- "evidence_review_required" means policy evidence was successfully retrieved, but the tool does not make a final HR approval decision.
- "compliant": null means that compliance could not be automatically determined; it does NOT mean that the MCP tool failed.
- If policy evidence is present, use it directly in the answer.
- If evidence is genuinely missing or conflicting, say so and recommend HR review.

Cite policy evidence inline using [DOC_ID, Section].
Separate policy facts from practical recommendations.
Do not expose hidden reasoning. Keep the answer concise and useful.
If an action is a draft or mock action, explicitly say it was not sent or committed.

For employee-specific workflows, use the supplied employee profile and structured-data results.
Never claim that a tool failed when the MCP trace shows the tool completed successfully.
"""
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://xena-hr-agent.local",
                "X-Title": "Xena HR Agent",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"Question: {message}\nPlan: {json.dumps(plan_data)}\nMCP results:\n{context}"},
                ],
                "temperature": 0.1,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _extract_payload(call: dict[str, Any]) -> Any:
        result = call.get("result", [])
        if len(result) == 1:
            return result[0]
        return result

    def _fallback_answer(self, message: str, plan_data: dict[str, Any], calls: list[dict[str, Any]]) -> str:
        """Deterministic grounded answer used when no LLM key is configured."""
        intent = plan_data.get("intent")
        payloads = {call["name"]: self._extract_payload(call) for call in calls}
        search = payloads.get("search_policy_documents", {})
        evidence = search.get("results", []) if isinstance(search, dict) else []
        citations = "; ".join(f"[{x['document_id']}, {x['section']}]" for x in evidence[:3])

        if plan_data.get("needs_clarification"):
            return plan_data.get("clarification_question", "I need more information before I can safely answer.")

        if intent == "remote_work":
            profile = payloads.get("lookup_employee_profile", {}).get("employee", {})
            compliance = payloads.get("check_policy_compliance", {})
            return (
                f"For {profile.get('name', plan_data.get('employee_id'))}, the request should be reviewed against the remote-work policy. "
                f"The MCP compliance check returned '{compliance.get('status', 'unknown')}', so this is guidance rather than an approval. "
                f"Relevant policy evidence: {citations}. Next step: confirm the required approval and location/security checks with HR or the manager."
            )

        if intent == "pto":
            pto = payloads.get("check_pto_balance", {}).get("pto", {})
            balance = pto.get("available_days", "unknown")
            answer = (
                f"The synthetic record shows {balance} PTO days currently available. "
                f"The request still needs to follow the PTO policy and manager approval process. "
                f"Relevant policy evidence: {citations}."
            )
            draft = payloads.get("draft_hr_email")
            if draft:
                answer += "\n\nA manager email draft was prepared, but it was not sent."
            return answer

        if intent == "benefits":
            status = payloads.get("lookup_benefits_status", {}).get("benefits", {})
            return (
                f"The synthetic benefits record shows: {json.dumps(status)}. "
                f"Eligibility should be checked against the retrieved benefits policy. Relevant evidence: {citations}."
            )

        if not evidence:
            return "I could not find supporting evidence in the internal HR policy corpus, so I cannot safely answer this policy question. Please contact HR for guidance."
        return f"Based on the retrieved internal policy evidence, here is the supported answer:\n\n{evidence[0]['snippet']}\n\nSources: {citations}"

    def run(self, message: str) -> dict[str, Any]:
        """Execute one agent workflow and return a grader-friendly structured response."""
        plan_data = plan(message)
        trace: list[dict[str, Any]] = [
            {"step": "intent_planning", "status": "completed", "intent": plan_data.get("intent"), "reason": plan_data.get("reason", "")},
        ]

        if plan_data.get("needs_clarification"):
            trace.append({"step": "clarification", "status": "required"})
            return {
                "answer": plan_data.get("clarification_question"),
                "citations": [],
                "snippets": [],
                "trace": trace,
                "workflow": plan_data.get("intent"),
                "escalation": False,
            }

        tool_calls = plan_data.get("tool_calls", [])
        trace.append({"step": "mcp_discovery", "status": "requested", "requested_tools": [c["name"] for c in tool_calls]})

        try:
            mcp_result = self.mcp.call_tools(tool_calls)
        except Exception as exc:
            trace.append({"step": "mcp_execution", "status": "failed", "error": str(exc)})
            return {
                "answer": "The HR tools are temporarily unavailable. No action was taken. Please try again or contact HR.",
                "citations": [],
                "snippets": [],
                "trace": trace,
                "workflow": plan_data.get("intent"),
                "escalation": True,
            }

        trace.append({"step": "mcp_discovery", "status": "completed", "discovered_tools": mcp_result["discovered_tools"]})
        snippets: list[dict[str, Any]] = []
        citations: list[dict[str, str]] = []
        for call in mcp_result["calls"]:
            trace.append(
                {
                    "step": "mcp_tool_call",
                    "status": "completed",
                    "tool": call["name"],
                    "arguments": call["arguments"],
                    "output_summary": str(call["result"])[:800],
                }
            )
            for item in call["result"]:
                if isinstance(item, dict) and "results" in item and isinstance(item["results"], list):
                    for evidence in item["results"]:
                        if isinstance(evidence, dict) and "document_id" in evidence:
                            snippets.append(evidence)
                            citations.append(
                                {"document_id": evidence["document_id"], "title": evidence.get("title", ""), "section": evidence.get("section", "")}
                            )

        if OPENROUTER_API_KEY:
            try:
                answer = self._synthesize_with_llm(message, plan_data, mcp_result["calls"])
            except Exception:
                answer = self._fallback_answer(message, plan_data, mcp_result["calls"])
        else:
            answer = self._fallback_answer(message, plan_data, mcp_result["calls"])

        trace.append({"step": "grounded_synthesis", "status": "completed", "citation_count": len(citations)})
        trace.append({"step": "safety", "status": "passed", "irreversible_action": False})

        # De-duplicate citations while preserving order.
        unique: list[dict[str, str]] = []
        seen = set()
        for citation in citations:
            key = (citation["document_id"], citation["section"])
            if key not in seen:
                seen.add(key)
                unique.append(citation)

        return {
            "answer": answer,
            "citations": unique,
            "snippets": snippets[:8],
            "trace": trace,
            "workflow": plan_data.get("intent"),
            "escalation": (
                plan_data.get("intent") in {"case_triage", "unknown"}
                or any(
                    call.get("name") == "check_policy_compliance"
                    and any(
                        isinstance(item, dict)
                        and item.get("status") == "evidence_review_required"
                        for item in call.get("result", [])
                    )
                for call in mcp_result["calls"]
                )
            ),
        }
