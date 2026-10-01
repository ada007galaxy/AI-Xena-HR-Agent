"""MCP client used by the agent orchestrator.

Each request launches the local MCP server as a subprocess, discovers its
available tools, calls the requested tools through the protocol, then closes
the session. This is simple, auditable and compatible with a single free-tier
service deployment.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from config import MCP_TIMEOUT_SECONDS


class MCPToolClient:
    """Discover and call tools exposed by the local MCP server."""

    def __init__(self) -> None:
        self.server_script = Path(__file__).resolve().parent / "server.py"
        self.discovered_tools: list[str] = []

    async def _session(self):
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.server_script)],
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        return stdio_client(params)

    async def _discover_and_call(self, calls: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
        """Discover tools, then invoke only the requested MCP tools."""
        async with await self._session() as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=MCP_TIMEOUT_SECONDS)
                listed = await asyncio.wait_for(session.list_tools(), timeout=MCP_TIMEOUT_SECONDS)
                names = [tool.name for tool in listed.tools]
                results: list[dict[str, Any]] = []
                for call in calls:
                    if call["name"] not in names:
                        raise RuntimeError(f"MCP tool not discovered: {call['name']}")
                    result = await asyncio.wait_for(
                        session.call_tool(call["name"], arguments=call.get("arguments", {})),
                        timeout=60,
                    )
                    content = []
                    for item in getattr(result, "content", []) or []:
                        if hasattr(item, "text"):
                            try:
                                content.append(json.loads(item.text))
                            except json.JSONDecodeError:
                                content.append(item.text)
                        else:
                            content.append(str(item))
                    results.append({"name": call["name"], "arguments": call.get("arguments", {}), "result": content})
                return names, results

    def discover_tools(self) -> list[str]:
        names, _ = asyncio.run(self._discover_and_call([]))
        self.discovered_tools = names
        return names

    def call_tools(self, calls: list[dict[str, Any]]) -> dict[str, Any]:
        names, results = asyncio.run(self._discover_and_call(calls))
        self.discovered_tools = names
        return {"discovered_tools": names, "calls": results}

    def health_check(self) -> dict[str, Any]:
        try:
            names = self.discover_tools()
            return {"status": "connected", "tool_count": len(names), "tools": names}
        except Exception as exc:
            return {"status": "unavailable", "error": str(exc)}
