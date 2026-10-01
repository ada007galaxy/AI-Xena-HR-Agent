"""Application and MCP smoke tests required by the assignment."""

from __future__ import annotations

import json

import pytest


def test_app_imports_and_health():
    from app import app

    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"


def test_demo_tasks_exist():
    from app import app

    client = app.test_client()
    response = client.get("/api/demo-tasks")
    data = response.get_json()
    assert response.status_code == 200
    assert len(data["tasks"]) >= 2


def test_mcp_tool_discovery_and_call():
    """The agent-side client must discover and call a real MCP-exposed tool."""
    try:
        from mcp_server.client import MCPToolClient
    except ImportError:
        pytest.skip("MCP SDK is not installed in this environment")

    client = MCPToolClient()
    names = client.discover_tools()
    assert "search_policy_documents" in names
    result = client.call_tools([
        {"name": "lookup_employee_profile", "arguments": {"employee_id": "EMP001"}}
    ])
    assert result["calls"][0]["name"] == "lookup_employee_profile"
    payload = result["calls"][0]["result"][0]
    assert payload["found"] is True


def test_unknown_employee_is_safe():
    from mcp_server.client import MCPToolClient

    result = MCPToolClient().call_tools([
        {"name": "lookup_employee_profile", "arguments": {"employee_id": "EMP999"}}
    ])
    payload = result["calls"][0]["result"][0]
    assert payload["found"] is False
