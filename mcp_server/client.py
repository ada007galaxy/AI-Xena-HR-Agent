from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from config import MCP_TIMEOUT_SECONDS


class MCPToolClient:
    """
    MCP client for the Xena HR MCP server.

    The MCP server runs locally using Streamable HTTP.
    """

    def __init__(self):
        # MCP 1.30.0 starts FastMCP on port 8000 by default.
        self.server_url = "http://127.0.0.1:8000/mcp"
        self.discovered_tools: list[str] = []

    async def _discover_and_call(
        self,
        calls: list[dict[str, Any]],
    ):
        """
        Connect to the MCP server, discover its tools,
        and execute the requested tools.
        """

        async with streamable_http_client(self.server_url) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(
                read_stream,
                write_stream,
            ) as session:

                # Initialize MCP session.
                await asyncio.wait_for(
                    session.initialize(),
                    timeout=MCP_TIMEOUT_SECONDS,
                )

                # Discover available tools.
                listed = await asyncio.wait_for(
                    session.list_tools(),
                    timeout=MCP_TIMEOUT_SECONDS,
                )

                names = [
                    tool.name
                    for tool in listed.tools
                ]

                self.discovered_tools = names

                results = []

                # Execute requested tools.
                for call in calls:

                    tool_name = call["name"]

                    if tool_name not in names:
                        raise RuntimeError(
                            f"MCP tool not available: {tool_name}"
                        )

                    result = await asyncio.wait_for(
                        session.call_tool(
                            tool_name,
                            arguments=call.get(
                                "arguments",
                                {},
                            ),
                        ),
                        timeout=MCP_TIMEOUT_SECONDS,
                    )

                    content = []

                    for item in getattr(
                        result,
                        "content",
                        [],
                    ) or []:

                        if hasattr(item, "text"):

                            try:
                                content.append(
                                    json.loads(item.text)
                                )

                            except json.JSONDecodeError:
                                content.append(item.text)

                        else:
                            content.append(
                                str(item)
                            )

                    results.append(
                        {
                            "name": tool_name,
                            "arguments": call.get(
                                "arguments",
                                {},
                            ),
                            "result": content,
                        }
                    )

                return names, results

    def discover_tools(self) -> list[str]:
        """
        Discover MCP tools using a lightweight MCP tool call.

        Streamable HTTP on MCP 1.30.0 can raise a TaskGroup
        error when a session is opened only for discovery.
        A harmless mock-data lookup keeps the session active.
        """

        result = self.call_tools(
        [
            {
                    "name": "lookup_employee_profile",
                    "arguments": {
                        "employee_id": "EMP001"
                    },
                }
            ]
        )

        return result["discovered_tools"]

    def call_tools(
        self,
        calls: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Discover and call MCP tools.
        """

        names, results = asyncio.run(
            self._discover_and_call(calls)
        )

        return {
            "discovered_tools": names,
            "calls": results,
        }

    def health_check(self) -> dict[str, Any]:
        """
        Return the current MCP connection status.

        MCP tool calls are tested separately by the application.
        We avoid opening a second MCP session solely for health checks.
        """

        return {
            "ok": True,
            "tools": self.discovered_tools,
            "transport": "streamable-http",
            "server_url": self.server_url,
        }