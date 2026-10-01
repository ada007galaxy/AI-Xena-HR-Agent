import subprocess
import sys
import time


print("Starting Xena MCP server...")

mcp_process = subprocess.Popen(
    [sys.executable, "mcp_server/server.py"]
)

print("Waiting for MCP server...")
time.sleep(5)

print("Starting Xena web application...")

try:
    subprocess.run(
        [
            sys.executable,
            "app.py",
        ],
        check=True,
    )
finally:
    print("Stopping MCP server...")
    mcp_process.terminate()