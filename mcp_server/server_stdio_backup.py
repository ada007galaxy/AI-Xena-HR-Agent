"""MCP server exposing synthetic HR tools.

The agent does not import these functions directly. It starts this process,
discovers the MCP tools, and invokes them through the MCP protocol over stdio.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
import sys
from contextlib import redirect_stdout, redirect_stderr

# Add the project root to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag_pipeline import get_rag

from typing import Any

from mcp.server.fastmcp import FastMCP
def _get_rag_safely():
    """Load the RAG system without writing model output to the MCP stdout stream."""
    with redirect_stdout(sys.stderr), redirect_stderr(sys.stderr):
        return get_rag()


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "mock_data"

mcp = FastMCP("Xena HR MCP Server")


# Load the RAG system once when the MCP server starts.
# This avoids loading the embedding model during every MCP tool call.
with redirect_stdout(sys.stderr), redirect_stderr(sys.stderr):
    RAG = get_rag()


def _load_json(name: str) -> Any:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


@mcp.tool()
def search_policy_documents(query: str, k: int = 4) -> dict[str, Any]:
    """Search the HR policy RAG index."""

    print(f"MCP RAG search started: {query}", file=sys.stderr)

    results = RAG.search(
        query,
        k=max(1, min(k, 8))
    )

    print(
        f"MCP RAG search finished: {len(results)} results",
        file=sys.stderr
    )

    return {
        "query": query,
        "results": results
    }


@mcp.tool()
def get_policy_section(document_id: str, section: str) -> dict[str, Any]:
    """Retrieve a named section from a specific policy document."""
    return {
        "document_id": document_id,
        "section": section,
        "results": RAG.get_section(document_id, section),
    }


@mcp.tool()
def lookup_employee_profile(employee_id: str) -> dict[str, Any]:
    """Look up synthetic employee data by employee ID."""
    employees = _load_json("employees.json")
    employee = next((e for e in employees if e["employee_id"] == employee_id), None)
    if not employee:
        return {"found": False, "employee_id": employee_id, "error": "Employee ID not found."}
    return {"found": True, "employee": employee}


@mcp.tool()
def check_pto_balance(employee_id: str) -> dict[str, Any]:
    """Return the synthetic PTO balance for an employee."""
    balances = _load_json("pto_balances.json")
    balance = balances.get(employee_id)
    if balance is None:
        return {"found": False, "employee_id": employee_id, "error": "PTO balance not found."}
    return {"found": True, "employee_id": employee_id, "pto": balance}


@mcp.tool()
def lookup_benefits_status(employee_id: str) -> dict[str, Any]:
    """Return synthetic benefits enrolment information."""
    benefits = _load_json("benefits.json")
    status = benefits.get(employee_id)
    if status is None:
        return {"found": False, "employee_id": employee_id, "error": "Benefits record not found."}
    return {"found": True, "employee_id": employee_id, "benefits": status}


@mcp.tool()
def check_policy_compliance(policy_area: str, employee_id: str, details: str) -> dict[str, Any]:
    """Run a transparent, mock compliance check using policy evidence and employee context."""
    profile = lookup_employee_profile(employee_id)
    if not profile.get("found"):
        return {"compliant": False, "status": "cannot_determine", "reason": "Employee not found."}

    evidence = search_policy_documents(f"{policy_area} {details}", k=4)
    enough_evidence = bool(evidence["results"])
    # This is deliberately conservative: the tool never invents a compliance approval.
    return {
        "compliant": None,
        "status": "evidence_review_required" if enough_evidence else "insufficient_evidence",
        "employee_id": employee_id,
        "policy_area": policy_area,
        "details": details,
        "evidence": evidence["results"],
        "note": "Final HR approval is not automated; the result is guidance based on retrieved policy evidence.",
    }


@mcp.tool()
def create_mock_hr_ticket(employee_id: str, subject: str, summary: str) -> dict[str, Any]:
    """Create a non-production mock HR ticket; no real HR system is changed."""
    return {
        "created": True,
        "mock": True,
        "ticket_id": f"MOCK-{uuid.uuid4().hex[:8].upper()}",
        "employee_id": employee_id,
        "subject": subject,
        "summary": summary,
        "message": "This is a simulated ticket for demonstration only.",
    }


@mcp.tool()
def draft_hr_email(employee_id: str, purpose: str, key_points: str) -> dict[str, Any]:
    """Draft a message without sending it or contacting a real person."""
    profile = lookup_employee_profile(employee_id)
    name = profile.get("employee", {}).get("name", "Employee")
    return {
        "drafted": True,
        "sent": False,
        "mock": True,
        "to": profile.get("employee", {}).get("manager", "Manager"),
        "subject": purpose,
        "body": f"Hi,\n\n{key_points}\n\nThanks,\n{name}",
        "message": "Draft only. No email has been sent.",
    }


if __name__ == "__main__":
    mcp.run()
