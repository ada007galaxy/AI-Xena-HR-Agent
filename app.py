"""Flask web application for the Xena HR Agent."""

from __future__ import annotations

import os
from flask import Flask, jsonify, render_template, request

from agent.orchestrator import AgentOrchestrator
from mcp_server.client import MCPToolClient

app = Flask(__name__)

# Create the orchestrator once so the web process can reuse configuration.
orchestrator = AgentOrchestrator(MCPToolClient())


@app.get("/")
def home():
    """Render the user-friendly chat interface."""
    return render_template("index.html")


@app.get("/health")
def health():
    """Return a lightweight health report suitable for Render checks."""
    mcp_status = orchestrator.mcp.health_check()
    return jsonify(
        {
            "status": "ok",
            "app": "Xena HR Agent",
            "mcp": mcp_status,
            "llm_provider": "openrouter" if os.getenv("OPENROUTER_API_KEY") else "demo-fallback",
        }
    )


@app.get("/api/demo-tasks")
def demo_tasks():
    """Return two deterministic demo prompts required by the assignment."""
    return jsonify(
        {
            "tasks": [
                {
                    "id": "remote-work",
                    "title": "Remote work eligibility",
                    "prompt": (
                        "EMP001 wants to work remotely from another UK region for six weeks. "
                        "Is this allowed, what checks are required, and what should they do next?"
                    ),
                },
                {
                    "id": "pto-request",
                    "title": "PTO request guidance",
                    "prompt": (
                        "EMP001 wants to take 3 days of PTO next week. Check their balance, "
                        "the PTO policy, approval requirements, and draft the next-step message."
                    ),
                },
            ]
        }
    )


@app.post("/chat")
def chat():
    """Process a user request and return answer, citations, snippets and trace."""
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Please enter an HR question or task."}), 400

    try:
        result = orchestrator.run(message)
        return jsonify(result)
    except Exception as exc:  # Keep failures useful and safe for the UI.
        return jsonify(
            {
                "error": "The request could not be completed safely.",
                "detail": str(exc),
                "trace": [{"step": "error", "status": "failed"}],
            }
        ), 500


if __name__ == "__main__":
    # Render supplies PORT; local development defaults to 5000.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
